from dataclasses import dataclass
from datetime import timedelta
import json
import os

from boto3 import client


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
        return f"[{timestamp}] {self.speaker}: {self.content}"


def convert_transcript(raw_data_path):
    lines = [Line()]
    output_path = f"{raw_data_path}.txt"
    with open(output_path, "w+") as f:
        # Pull transcription data out of file
        with open(raw_data_path) as raw_data:
            data = json.load(raw_data)

        # Generate a series of lines from the given transcribed items, each line represents a distinct speaker
        for item in data["results"]["items"]:
            # finish the current line and start a new one if this content has a new speaker
            if item.get("speaker_label", lines[-1].speaker) != lines[-1].speaker:
                lines.append(
                    Line(speaker=item["speaker_label"], time=item["start_time"])
                )
            lines[-1].content += item["alternatives"][0]["content"]

        f.writelines([str(line) for line in lines])
    return output_path


def lambda_handler(event, _):
    s3 = client("s3")

    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        file_name = os.path.basename(key)
        raw_data_path = f"/tmp/{file_name}"
        s3.download_file(bucket, key, raw_data_path)
        s3.upload_file(
            convert_transcript(raw_data_path), bucket, f"output/{file_name}.txt"
        )

    return {
        "statusCode": 200,
        "body": json.dumps("Transcription Beautification Finished"),
    }
