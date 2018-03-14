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
source_video_path = "tractor.mp4"


## Bitrates to test (in kbps)
#bitrates = [
#	"100000k",
#	"80000k",
#	"60000k",
#	"40000k",
#	"20000k",
#	"10000k",
#	"5000k",
#	"1000k",
#	"500k",
#	"250k"
#]
bitrates = [
	"400k",
	"375k",
	"350k",
	"325k",
	"300k"
]


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


## CABAC line parsing regex
cabac_regex = re.compile(
	"^\s(?P<syntax_element>\S+)\s+:\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(?P<total_bits>-?\d+)\s\(\s+(-?\d+)\)\s$"
)


## CAVLC line parsing regex
cavlc_regex = re.compile(
	"^\s(?P<syntax_element>\S+)\s+:\s+-\s+-\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(?P<total_bits>-?\d+)\s\(\s+(-?\d+)\)\s$"
)


## Stats parsing regex
stats_regex = re.compile(
	"encoded (?P<frames>\d+) frames? in \d+\.?\d*s \(\d+\.?\d* fps\), \d+\.?\d* kb/s, Avg QP:(?P<qp>\d+\.?\d*), Global PSNR: (?P<psnr>\d+\.?\d*)"
)


## FPS parsing regex
fps_regex = re.compile(
	"Stream #\d.*\s(?P<fps>\d+\.?\d*)\s*fps"
)


## Frame stats parsing regexes
iframes_regex = re.compile(
	"x265 \[info]: frame I:\s*(?P<count>\d+),\s*Avg QP:\s*(?P<qp>\d+\.?\d*)\s*kb/s:\s*(?P<kbps>\d+\.?\d*)\s*PSNR Mean:\s*Y:\s*(?P<psnr_y>\d+\.?\d*)\s*U:\s*(?P<psnr_u>\d+\.?\d*)\s*V:\s*(?P<psnr_v>\d+\.?\d*)"
)
pframes_regex = re.compile(
	"x265 \[info]: frame P:\s*(?P<count>\d+),\s*Avg QP:\s*(?P<qp>\d+\.?\d*)\s*kb/s:\s*(?P<kbps>\d+\.?\d*)\s*PSNR Mean:\s*Y:\s*(?P<psnr_y>\d+\.?\d*)\s*U:\s*(?P<psnr_u>\d+\.?\d*)\s*V:\s*(?P<psnr_v>\d+\.?\d*)"
)
bframes_regex = re.compile(
	"x265 \[info]: frame B:\s*(?P<count>\d+),\s*Avg QP:\s*(?P<qp>\d+\.?\d*)\s*kb/s:\s*(?P<kbps>\d+\.?\d*)\s*PSNR Mean:\s*Y:\s*(?P<psnr_y>\d+\.?\d*)\s*U:\s*(?P<psnr_u>\d+\.?\d*)\s*V:\s*(?P<psnr_v>\d+\.?\d*)"
)




################################################################################
#
# Methods
#
################################################################################

## Runs ffmpeg to extract the raw hevc bitstream from a video file
def extract_hevc_bitstream(mp4_video_in, hevc_bitstream_out):
	subprocess.run([
		"ffmpeg",
		"-i", mp4_video_in,
		"-c:v", "copy",
		"-bsf", "hevc_mp4toannexb",
		hevc_bitstream_out
	], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


## Performs two-pass encoding via x265 with ffmpeg to recode a given video file,
##   achieving a target bitrate. Returns the ffmpeg output text
##
## See https://trac.ffmpeg.org/wiki/Encode/H.265#Two-PassExample
def recode_video(video, bitrate):
	subprocess.run([
		"ffmpeg",
		"-y",
		"-i", video,
		"-c:v", "libx265",
		"-b:v", bitrate,
		"-x265-params", ":".join([
			"pass=1",
			"keyint=-1",
			"bframes=0"
		]),
		"-c:a", "aac",
		"-b:a", "128k",
		"-f", "mp4",
		"NUL" # "NUL" on Windows, "/dev/null" on linux
	], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	
	return subprocess.run([
		"ffmpeg",
		"-i", video,
		"-c:v", "libx265",
		"-b:v", bitrate,
		"-x265-params", ":".join([
			"pass=2",
			"keyint=-1",
			"bframes=0"
		]),
		"-c:a", "aac",
		"-b:a", "128k",
		"-psnr",
		recoded_video_file_name
	], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


## Prints a results data structure to stdout
def print_results(data):
	seconds = data['frames'] / data['fps']
	print("\t".join([
		bitrate[:-1],
		str(data['bitstream_size'] / 1000 / seconds),
		str(data['prediction'] / 1000 / seconds),
		str(data['residual'] / 1000 / seconds),
		str(data['other'] / 1000 / seconds),
		str(data['psnr']),
		str(data['qp'])
	]))


## Tries to delete any file that this script may have created; fails silently
##   for files which can't be deleted
def clean_up_files(bitrate):
	try:
		os.remove("x265_2pass.log")
	except:
		pass
	
	try:
		os.remove("x265_2pass.log.cutree")
	except:
		pass
	
	try:
		os.remove(extracted_bitstream_file_name)
	except:
		pass
	
	try:
		if save_recoded_videos:
			os.rename(recoded_video_file_name, bitrate + "_" + recoded_video_file_name)
		else:
			os.remove(recoded_video_file_name)
	except:
		pass




################################################################################
#
# Script
#
################################################################################

## Data structure for storing results
results = {}


## Print header
print("\t".join([
	"target_bitrate_kbps",
	"achieved_bitrate_kbps",
	"prediction_kbps",
	"residual_kbps",
	"other_kbps",
	"avg_psnr",
	"avg_qp"
]))


## Bitrate loop
for bitrate in bitrates:
	try:
		## Initialize entry in results dictionary
		results[bitrate] = {
			'prediction': 0,
			'residual': 0,
			'other': 0
		}
		
		
		## Recode video to target bitrate
		result = recode_video(source_video_path, bitrate)
		output = result.stderr.decode('utf-8')
		
		
		## Capture average qp, number of frames, psnr
		stats_match = stats_regex.search(output)
		results[bitrate]['frames'] = int(stats_match.group("frames"))
		results[bitrate]['qp']     = float(stats_match.group("qp"))
		results[bitrate]['psnr']   = float(stats_match.group("psnr"))
		
		
		## Capture frame rate
		fps_match = fps_regex.search(output)
		results[bitrate]['fps'] = float(fps_match.group("fps"))
		
		
		## Capture i-frame statistics
		iframes_match = iframes_regex.search(output)
		if iframes_match:
			results[bitrate]['iframes'] = float(iframes_match.group("count"))
		else:
			results[bitrate]['iframes'] = 0.0
		
		
		## Capture p-frame statistics
		pframes_match = pframes_regex.search(output)
		if pframes_match:
			results[bitrate]['pframes'] = float(pframes_match.group("count"))
		else:
			results[bitrate]['pframes'] = 0.0
		
		
		## Capture b-frame statistics
		bframes_match = bframes_regex.search(output)
		if bframes_match:
			results[bitrate]['bframes'] = float(bframes_match.group("count"))
		else:
			results[bitrate]['bframes'] = 0.0
		
		
		## Extract raw h265 bitstream from video container format
		extract_hevc_bitstream(recoded_video_file_name, extracted_bitstream_file_name)
		
		
		## Save hevc bitstream size
		results[bitrate]['bitstream_size'] = os.path.getsize(extracted_bitstream_file_name) * 8
		
		
		## Run bit count decoder
		result = subprocess.run([
			bit_count_decoder_path,
			"-b", extracted_bitstream_file_name
		], stdout=subprocess.PIPE)
		output = result.stdout.decode('utf-8')
		lines  = output.splitlines()
		
		
		## Parse bit count output line-by-line
		for line in lines:
			cabac_match = cabac_regex.match(line)
			cavlc_match = cavlc_regex.match(line)
			if cabac_match:
				if cabac_match.group('syntax_element') in excluded_keys:
					pass
				elif cabac_match.group('syntax_element') in prediction_keys:
					results[bitrate]['prediction'] += int(cabac_match.group('total_bits'))
				elif cabac_match.group('syntax_element') in residual_keys:
					results[bitrate]['residual'] += int(cabac_match.group('total_bits'))
				else:
					results[bitrate]['other'] += int(cabac_match.group('total_bits'))
			elif cavlc_match:
				if cavlc_match.group('syntax_element') in excluded_keys:
					pass
				if cavlc_match.group('syntax_element') in prediction_keys:
					results[bitrate]['prediction'] += int(cavlc_match.group('total_bits'))
				elif cavlc_match.group('syntax_element') in residual_keys:
					results[bitrate]['residual'] += int(cavlc_match.group('total_bits'))
				else:
					results[bitrate]['other'] += int(cavlc_match.group('total_bits'))
		
		
		## Print results for this bitrate
		print_results(results[bitrate])
	
	
	## Do our best to clean files
	finally:
		clean_up_files(bitrate)