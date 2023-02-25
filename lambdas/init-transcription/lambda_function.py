import json
import os

from boto3 import client


def lambda_handler(event, ctx):
    transcribe = client("transcribe")
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        file_name = os.path.basename(key)

        uri = client("s3").generate_presigned_url(
            "get_object", ExpiresIn=600, Params={"Bucket": bucket, "Key": key}
        )
        transcribe.start_transcription_job(
            TranscriptionJobName=file_name,
            Media={"MediaFileUri": uri},
            MediaFormat="mp3",
            LanguageCode="en-US",
            ShowSpeakerLabels=True,
            OutputBucketName=bucket,
            OutputKey=f"/output/{file_name}",
        )
        print(f"Started transcription job {file_name}.")
    return {
        "statusCode": 200,
        "body": json.dumps("Transcription Beautification Finished"),
    }
