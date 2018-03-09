import subprocess
import pprint
import os
import re



################################################################################
#
# Input parameters
#
################################################################################

## Path of source video file
source_video_path = "jellyfish.mp4"


## Bitrates to test (in kbps)
bitrates = [
	"100000k",
	"80000k",
	"60000k",
	"40000k",
	"20000k",
	"10000k",
	"5000k",
	"1000k",
	"500k",
	"250k"
]
#bitrates = [
#	"400k",
#	"375k",
#	"350k",
#	"325k",
#	"300k"
#]


## If true, the recoded videos will be saved in the current directory
save_recoded_videos = False




################################################################################
#
# Constants
#
################################################################################

## List of all syntax element keys related to PREDICTION
prediction_keys = [
	"CABAC_BITS__SKIP_FLAG",
	"CABAC_BITS__MERGE_FLAG",
	"CABAC_BITS__MERGE_INDEX",
	"CABAC_BITS__MVP_IDX",
	"CABAC_BITS__PRED_MODE",
	"CABAC_BITS__INTRA_DIR_ANG",
	"CABAC_BITS__INTER_DIR",
	"CABAC_BITS__REF_FRM_IDX",
	"CABAC_BITS__MVD",
	"CABAC_BITS__MVD_EP",
	"CABAC_BITS__CROSS_COMPONENT_PREDICTION"
]


## List of all syntax element keys related to RESIDUAL
residual_keys = [
	"CABAC_BITS__TQ_BYPASS_FLAG",
	"CABAC_BITS__TRANSFORM_SUBDIV_FLAG",
	"CABAC_BITS__QT_ROOT_CBF",
	"CABAC_BITS__DELTA_QP_EP",
	"CABAC_BITS__CHROMA_QP_ADJUSTMENT",
	"CABAC_BITS__QT_CBF",
	"CABAC_BITS__TRANSFORM_SKIP_FLAGS",
	"CABAC_BITS__LAST_SIG_X_Y",
	"CABAC_BITS__SIG_COEFF_GROUP_FLAG",
	"CABAC_BITS__SIG_COEFF_MAP_FLAG",
	"CABAC_BITS__GT1_FLAG",
	"CABAC_BITS__GT2_FLAG",
	"CABAC_BITS__SIGN_BIT",
	"CABAC_BITS__ESCAPE_BITS",
	"EXPLICIT_RDPCM_BITS",
	"CABAC_EP_BIT_ALIGNMENT",
	"CABAC_BITS__ALIGNED_SIGN_BIT",
	"CABAC_BITS__ALIGNED_ESCAPE_BITS"
]


## List of all syntax element keys that should be EXCLUDED
excluded_keys = [
	"NAL_UNIT_TOTAL_BODY"
]


## Path to bit count decoder
bit_count_decoder_path = "../bin/vc2015/Win32/Release/TAppDecoder.exe"


## Recoded video file name
recoded_video_file_name = "recoded.mp4"


## Extracted hevc bitstream file name
extracted_bitstream_file_name = "recoded.h265"


## Command line input to extract hevc bitstream
extract_hevc_bitstream = [
	"ffmpeg",
	"-i", recoded_video_file_name,
	"-c:v", "copy",
	"-bsf", "hevc_mp4toannexb",
	extracted_bitstream_file_name
]


## Command line input to run the bit count decoder
bit_count_decoder = [
	bit_count_decoder_path,
	"-b", extracted_bitstream_file_name
]


## CABAC line parsing regex
cabac_regex = re.compile(
	"^\s(\S+)\s+:\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s\(\s+(-?\d+)\)\s$"
)


## CAVLC line parsing regex
cavlc_regex = re.compile(
	"^\s(\S+)\s+:\s+-\s+-\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s\(\s+(-?\d+)\)\s$"
)




################################################################################
#
# Script
#
################################################################################

## Data structure for storing results
results = {}


## Print header
print("\t".join(["total", "prediction", "residual", "other"]))


## Bitrate loop
for bitrate in bitrates:
	## Initialize entry in results dictionary
	results[bitrate] = {
		'prediction': 0,
		'residual': 0,
		'other': 0
	}
	
	
	## Recode video to target bitrate (2-pass encoding)
	## See https://trac.ffmpeg.org/wiki/Encode/H.265#Two-PassExample
	subprocess.run([
		"ffmpeg",
		"-y",
		"-i", source_video_path,
		"-c:v", "libx265",
		"-b:v", bitrate,
		"-x265-params", "pass=1",
		"-c:a", "aac",
		"-b:a", "128k",
		"-f", "mp4",
		"NUL" # "NUL" on Windows, "/dev/null" on linux
	], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	
	
	## Second encoding pass
	subprocess.run([
		"ffmpeg",
		"-i", source_video_path,
		"-c:v", "libx265",
		"-b:v", bitrate,
		"-x265-params", "pass=2",
		"-c:a", "aac",
		"-b:a", "128k",
		recoded_video_file_name
	], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	
	
	## Clean files
	os.remove("x265_2pass.log")
	os.remove("x265_2pass.log.cutree")
	
	
	## Extract raw h265 bitstream from video container format
	subprocess.run(extract_hevc_bitstream, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	
	
	## Clean files
	if save_recoded_videos:
		os.rename(recoded_video_file_name, bitrate + "_" + recoded_video_file_name)
	else:
		os.remove(recoded_video_file_name)
	
	
	## Save hevc bitstream size
	results[bitrate]['hevc_bistream_size'] = os.path.getsize(extracted_bitstream_file_name)
	
	
	## Run bit count decoder
	result = subprocess.run(bit_count_decoder, stdout=subprocess.PIPE)
	output = result.stdout.decode('utf-8')
	lines  = output.splitlines()
	
	
	## Clean files
	os.remove(extracted_bitstream_file_name)
	
	
	## Parse bit count output line-by-line
	for line in lines:
		cabac_match = cabac_regex.match(line)
		cavlc_match = cavlc_regex.match(line)
		if cabac_match:
			if cabac_match.group(1) in excluded_keys:
				pass
			elif cabac_match.group(1) in prediction_keys:
				results[bitrate]['prediction'] += int(cabac_match.group(10))
			elif cabac_match.group(1) in residual_keys:
				results[bitrate]['residual'] += int(cabac_match.group(10))
			else:
				results[bitrate]['other'] += int(cabac_match.group(10))
		elif cavlc_match:
			if cavlc_match.group(1) in excluded_keys:
				pass
			if cavlc_match.group(1) in prediction_keys:
				results[bitrate]['prediction'] += int(cavlc_match.group(5))
			elif cavlc_match.group(1) in residual_keys:
				results[bitrate]['residual'] += int(cavlc_match.group(5))
			else:
				results[bitrate]['other'] += int(cavlc_match.group(5))
	
	
	## Convert accumulated bits to bytes
	results[bitrate]['prediction'] /= 8
	results[bitrate]['residual']   /= 8
	results[bitrate]['other']      /= 8
	
	
	## Output results
	#pprint.pprint({ bitrate: results[bitrate] })
	print("\t".join([
		str(results[bitrate]['hevc_bistream_size']),
		str(results[bitrate]['prediction']),
		str(results[bitrate]['residual']),
		str(results[bitrate]['other'])
	]))