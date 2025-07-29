import warnings

warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=DeprecationWarning)

# GENERAL IMPORTS
import argparse
import sys
import numpy as np
import warnings
from pathlib import Path
import json
import logging
import boto3
from botocore import UNSIGNED
from botocore.client import Config


# SPIKEINTERFACE
import spikeinterface as si
import spikeinterface.extractors as se
import spikeinterface.preprocessing as spre

from spikeinterface.core.core_tools import SIJsonEncoder


data_folder = Path("../data")
results_folder = Path("../results")


# Define argument parser
parser = argparse.ArgumentParser(description="Dispatch jobs for CHRONIC ephys pipeline")

s3_path_group = parser.add_mutually_exclusive_group()
s3_path_help = "Path to s3 compressed zarr folder."
s3_path_group.add_argument("--s3-path", default=None, help=s3_path_help)
s3_path_group.add_argument("static_s3_path", nargs="?", default=None, help=s3_path_help)

chunk_duration_group = parser.add_mutually_exclusive_group()
chunk_duration_help = "Duration of each chunk in h. Use -1 to turn off chunking"
chunk_duration_group.add_argument("--chunk-duration", default=1, help=chunk_duration_help)
chunk_duration_group.add_argument("static_chunk_duration", nargs="?", default=None, help=chunk_duration_help)

inter_chunk_duration_group = parser.add_mutually_exclusive_group()
inter_chunk_duration_help = "Inter-chunk duration of each chunk in h."
inter_chunk_duration_group.add_argument("--inter-chunk-duration", default=24, help=inter_chunk_duration_help)
inter_chunk_duration_group.add_argument("static_inter_chunk_duration", nargs="?", default=None, help=inter_chunk_duration_help)

split_group = parser.add_mutually_exclusive_group()
split_help = "Whether to process different groups separately. Default: split groups"
split_group.add_argument("--no-split-groups", action="store_true", help=split_help)
split_group.add_argument("static_split_groups", nargs="?", default="false", help=split_help)

start_hour_group = parser.add_mutually_exclusive_group()
start_hour_help = "Start time in h."
start_hour_group.add_argument("--start-time-h", default=None, help=start_hour_help)
start_hour_group.add_argument("static_start_time_h", nargs="?", default=None, help=start_hour_help)

end_hour_group = parser.add_mutually_exclusive_group()
end_hour_help = "End time in h."
end_hour_group.add_argument("--end-time-h", default=None, help=end_hour_help)
end_hour_group.add_argument("static_end_time_h", nargs="?", default=None, help=end_hour_help)

invert_group = parser.add_mutually_exclusive_group()
invert_help = "Whether to invert the signal"
invert_group.add_argument("--invert", action="store_true", help=invert_help)
invert_group.add_argument("static_invert", nargs="?", default="false", help=invert_help)


if __name__ == "__main__":
    args = parser.parse_args()

    S3_PATH = args.static_s3_path or args.s3_path
    assert S3_PATH is not None, "S3 path must be provided"
    CHUNK_DURATION = float(args.static_chunk_duration or args.chunk_duration)
    INTER_CHUNK_DURATION = float(args.static_inter_chunk_duration or args.inter_chunk_duration)
    SPLIT_GROUPS = (
        True if args.static_split_groups and args.static_split_groups.lower() == "true" else not args.no_split_groups
    )
    START_TIME_H = args.static_start_time_h or args.start_time_h
    if START_TIME_H is not None and START_TIME_H == "":
        START_TIME_H = None
    END_TIME_H = args.static_end_time_h or args.end_time_h
    if END_TIME_H is not None and END_TIME_H == "":
        END_TIME_H = None
    INVERT = True if args.static_invert and args.static_invert.lower() == "true" else args.invert

    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")

    logging.info(f"Running job dispatcher with the following parameters:")
    logging.info(f"\tS3 PATH: {S3_PATH}")
    logging.info(f"\tCHUNK_DURATION: {CHUNK_DURATION}")
    logging.info(f"\tINTER_CHUNK_DURATION: {INTER_CHUNK_DURATION}")
    logging.info(f"\tSTART_TIME_H: {START_TIME_H}")
    logging.info(f"\tEND_TIME_H: {END_TIME_H}")
    logging.info(f"\tINVERT: {INVERT}")

    logging.info(f"Parsing CHRONIC input folder")
    recording_dict = {}

    # Create an anonymous S3 client
    s3 = boto3.client('s3')
    s3_unsigned = boto3.client('s3', config=Config(signature_version=UNSIGNED))

    if S3_PATH.endswith("/"):
        s3_path = S3_PATH[:-1]
    else:
        s3_path = S3_PATH

    # add ecephys/ecephys_compressed
    session_s3_path = s3_path
    s3_path = f"{s3_path}/ecephys/ecephys_compressed/experiment1_AmplifierData.zarr"

    slash_splits = s3_path.split("//")[1].split("/")
    bucket_name = slash_splits[0]
    session_name = slash_splits[1]
    stream_name = slash_splits[-1]
    stream_name = stream_name[:stream_name.find(".zarr")]

    logging.info(f"\tSession name: {session_name}")

    recording_name = f"{stream_name}_recording"
    recording_full = si.load(s3_path)
    # invert the signal
    if INVERT:
        logging.info(f"\tInverting signal polarity")
        recording_full = spre.scale(recording_full, gain=-1)

    logging.info(f"\tLoaded full recording: {recording_full}")

    if START_TIME_H is not None or END_TIME_H is not None:
        start_time_s = float(START_TIME_H) * 3600 if START_TIME_H else 0
        end_time_s = float(END_TIME_H) * 3600 if END_TIME_H else recording_full.get_end_time()
        recording = recording_full.time_slice(start_time=start_time_s, end_time=end_time_s)
        logging.info(f"\tTime-sliced recording: {recording}")
    else:
        recording = recording_full

    if CHUNK_DURATION > 0:
        assert INTER_CHUNK_DURATION > CHUNK_DURATION
        chunk_duration_s = CHUNK_DURATION * 3600
        inter_chunk_duration_s = INTER_CHUNK_DURATION * 3600
        start_time = recording.get_start_time()
        end_time = recording.get_end_time()
        start_times = np.arange(start_time, end_time, inter_chunk_duration_s)

        logging.info(f"\tConcatenating {len(start_times)} chunks")

        recording_list = []
        for start_time in start_times:
            rec_sub = recording.time_slice(start_time=start_time, end_time=start_time + chunk_duration_s)
            recording_list.append(rec_sub)

            # final concatenation
            recording_concat = si.concatenate_recordings(recording_list)
        logging.info(f"\tConcatenated recording: {recording_concat}")
    else:
        recording_concat = recording
        
    recording_dict[(session_name, recording_name)] = {}
    recording_dict[(session_name, recording_name)]["raw"] = recording_concat


    # populate job dict list
    job_dict_list = []
    logging.info("Recording to be processed in parallel:")
    for session_recording_name in recording_dict:
        session_name, recording_name = session_recording_name
        recording = recording_dict[session_recording_name]["raw"]

        recordings = [recording]

        for recording_index, recording in enumerate(recordings):
            recording_name_segment = f"{recording_name}{recording_index + 1}"

            duration = np.round(recording.get_total_duration(), 2)

            # if multiple channel groups, process in parallel
            if SPLIT_GROUPS and len(np.unique(recording.get_channel_groups())) > 1:
                for group_name, recording_group in recording.split_by("group").items():
                    recording_name_group = f"{recording_name_segment}_group{group_name}"
                    job_dict = dict(
                        session_name=session_name,
                        recording_name=str(recording_name_group),
                        recording_dict=recording_group.to_dict(recursive=True),
                        duration=duration,
                        session_s3_path=session_s3_path,
                        skip_times=False,
                        debug=False,
                    )
                    rec_str = f"\t{recording_name_group}\n\t\tDuration {duration} s - Num. channels: {recording_group.get_num_channels()}"
                    logging.info(rec_str)
                    job_dict_list.append(job_dict)
            else:
                job_dict = dict(
                    session_name=session_name,
                    recording_name=str(recording_name_segment),
                    recording_dict=recording.to_dict(recursive=True),
                    duration=duration,
                    session_s3_path=session_s3_path,
                    skip_times=False,
                    debug=False,
                )
                rec_str = f"\t{recording_name_segment}\n\t\tDuration: {duration} s - Num. channels: {recording.get_num_channels()}"
                logging.info(rec_str)
                job_dict_list.append(job_dict)

    if not results_folder.is_dir():
        results_folder.mkdir(parents=True)

    for i, job_dict in enumerate(job_dict_list):
        with open(results_folder / f"job_{i}.json", "w") as f:
            json.dump(job_dict, f, indent=4, cls=SIJsonEncoder)

    ecephys_metadata_folder = results_folder / "ecephys_session"
    ecephys_metadata_folder.mkdir()

    metadata_json_files = ["data_description", "subject", "rig", "session", "processing"]
    for metadata_file_name in metadata_json_files:
        try:
            key = f"{session_name}/{metadata_file_name}.json"
            s3.download_file(bucket_name, key, ecephys_metadata_folder / f'{metadata_file_name}.json')
        except Exception as e:
            # try unsigned
            try:
                s3_unsigned.download_file(bucket_name, key, ecephys_metadata_folder / f'{metadata_file_name}.json')
            except Exception as e2:
                logging.info(f"Could not download {metadata_file_name}.json. Error: {e2}")
    logging.info(f"Generated {len(job_dict_list)} job config files")
