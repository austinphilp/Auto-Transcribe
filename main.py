from time import sleep
import sys
from dataclasses import dataclass
from datetime import timedelta, datetime
import json

import boto3
from botocore.config import Config

BUCKET = "rooted-psychiatry-test-transcription"
INPUT_PREFIX = "input"
OUTPUT_PREFIX = "output"

config = Config(region_name="us-west-2")
s3 = boto3.client("s3", config=Config(region_name="us-west-2"))
transcribe = boto3.client("transcribe", config=Config(region_name="us-west-2"))


@dataclass
class Line:
    """Tracks each line of speach"""

    # the first speaker will always be labeled spk_0
    speaker: str = "spk_0"
    content: str = ""
    time: int = 0

    def __str__(self):
        # Get timestamp in HH:MM:SS format
        timestamp = str(timedelta(seconds=round(float(self.time))))
        return f"[{timestamp}] {self.speaker}: {self.content}\n\n"


def upload_to_s3(file_name):
    """Upload a JSON file to S3 using the given file name"""
    # Upload the file
    key = f"{INPUT_PREFIX}/{file_name}"
    s3.upload_file(file_name, BUCKET, key)
    return key


def download_from_s3_to_dict(key):
    """Download a JSON file from S3 and load it to a dict"""
    obj = boto3.resource("s3").Object(BUCKET, key)
    return json.loads(obj.get()["Body"].read().decode("utf-8"))


def convert_transcript(data, output_path):
    """Convert the obtuse format used by AWS to something human readable and write it to the output_path"""
    lines = [Line()]
    with open(output_path, "w+") as f:
        # Generate a series of lines from the given transcribed items, each line represents a distinct speaker
        for item in data["results"]["items"]:
            if item["type"] == "punctuation":
                # if we're about to add punction, remove the last space
                lines[-1].content = lines[-1].content[:-1]
            # finish the current line and start a new one if this content has a new speaker
            if item.get("speaker_label", lines[-1].speaker) != lines[-1].speaker:
                lines.append(
                    Line(speaker=item["speaker_label"], time=item["start_time"])
                )
            lines[-1].content += item["alternatives"][0]["content"] + " "

        f.writelines([str(line) for line in lines])
    return output_path


def do_transcription(key, file_name, num_speakers):
    """Run a transcription job, waiting for the job to complete before downloading the transcription JSON to a dict"""
    uri = f"https://s3-us-west-2.amazonaws.com/{BUCKET}/{key}"
    output_key = f"/output/{file_name}.json"
    job_name = f"{file_name}-{datetime.now().timestamp()}"
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": uri},
        MediaFormat="mp4",
        LanguageCode="en-US",
        Settings={"ShowSpeakerLabels": True, "MaxSpeakerLabels": num_speakers},
        OutputBucketName=BUCKET,
        OutputKey=f"/output/{file_name}.json",
    )
    wait_for_transcription_job(job_name)
    data = download_from_s3_to_dict(output_key)
    s3.delete_object(Bucket=BUCKET, Key=key)
    s3.delete_object(Bucket=BUCKET, Key=output_key)
    return data


def wait_for_transcription_job(job_name):
    """Wait until the status for the transaction job is 'complete'"""
    print("The gnomes are gnoming... Go get a coffee and check back in a few")
    i = 1
    while True:
        if i % 6 == 0:
            print("Fear not, the gnomes are still at it!")
        response = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        status = response["TranscriptionJob"]["TranscriptionJobStatus"]
        if status == "COMPLETED":
            return
        elif status == "FAILED":
            print(
                "Uh oh.. Things have gone terribly wrong. Go put your husband to work!"
            )
            sys.exit(1)
        else:
            print(status)
        i += 1
        sleep(10)


if __name__ == "__main__":
    file_name = input("Drag and drop the file you would like to transribe: ")
    speakers = min(
        int(
            input(
                "How many participants are on this call (enter '10' if you're unsure)? "
            )
        ),
        10,
    )
    print(
        "Great! Kick back and relax, we're letting the internet gnomes out of their cages and getting ready to go!"
    )
    print(f"loading slingshot to send {file_name} to the cloud..")
    key = upload_to_s3(file_name)
    print("Summoning internet gnomes to watch the video and jot down their notes...")
    transcription = do_transcription(key, file_name, speakers)
    print("Converting Gnomish to English")
    convert_transcript(transcription, f"{file_name}-transcript.txt")
    print("Finished!")
