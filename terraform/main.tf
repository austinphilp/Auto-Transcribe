resource "aws_s3_bucket" "transcription" {
   bucket = "rooted-psychiatry-test-transcription"
   tags = {
     Name = "Transcription"
   }
}

resource "aws_s3_bucket_acl" "bucket_acl" {
  bucket = aws_s3_bucket.transcription.id
  acl    = "private"
}

resource "aws_s3_bucket_lifecycle_configuration" "bucket-config" {
  bucket = aws_s3_bucket.transcription.id
  rule {
    id = "input"
    expiration {
      days = 1
    }
    filter {
      and {
        prefix = "input/"
        tags = {
          rule      = "input"
          autoclean = "true"
        }
      }
    }
    status = "Enabled"
  }
  rule {
    id = "output"
    expiration {
      days = 1
    }
    filter {
      and {
        prefix = "output/"
        tags = {
          rule      = "output"
          autoclean = "true"
        }
      }
    }
    status = "Enabled"
  }
  rule {
    id = "final"
    expiration {
      days = 1
    }
    filter {
      and {
        prefix = "final/"
        tags = {
          rule      = "final"
          autoclean = "true"
        }
      }
    }
    status = "Enabled"
  }
}


resource "aws_iam_role" "lambda_role" {
  name   = "Transcription_Lambda_Role"
  assume_role_policy = <<EOF
  {
   "Version": "2012-10-17",
   "Statement": [
     {
       "Action": "sts:AssumeRole",
       "Principal": {
         "Service": "lambda.amazonaws.com"
       },
       "Effect": "Allow",
       "Sid": ""
     }
   ]
  }
  EOF
}

# resource "aws_iam_policy" "" {
#   name         = "aws_iam_policy_for_transcription_lambda_role"
#   path         = "/"
#   description  = "AWS IAM Policy for managing transcription lambdas"
#   policy = "AmazonS3FullAccess"
# }

data "aws_iam_policy" "iam_policy_for_s3" {
  arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "attach_s3_iam_policy_to_iam_role" {
 role        = aws_iam_role.lambda_role.name
 policy_arn  = data.aws_iam_policy.iam_policy_for_s3.arn
}

resource "aws_iam_role_policy_attachment" "attach_lambda_iam_policy_to_iam_role" {
 role        = aws_iam_role.lambda_role.name
 policy_arn  = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


data "archive_file" "init_transcription_archive" {
  type        = "zip"
  source_dir  = "${path.module}/../lambdas/init-transcription/"
  output_path = "${path.module}/../lambdas/init-transcription.zip"
}

data "archive_file" "beautify_transcription_archive" {
  type        = "zip"
  source_dir  = "${path.module}/../lambdas/beautify-transcription/"
  output_path = "${path.module}/../lambdas/beautify-transcription.zip"
}

resource "aws_lambda_function" "init_transcription_func" {
  filename      = "${path.module}/../lambdas/init-transcription.zip"
  function_name = "init_transcription"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.8"
  depends_on    = [aws_iam_role_policy_attachment.attach_s3_iam_policy_to_iam_role]
}

resource "aws_lambda_function" "beautify_transcription_func" {
  filename      = "${path.module}/../lambdas/beautify-transcription.zip"
  function_name = "beautify_transcription"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.8"
  depends_on    = [aws_iam_role_policy_attachment.attach_s3_iam_policy_to_iam_role]
}

resource "aws_s3_bucket_notification" "input_file_trigger" {
  bucket = aws_s3_bucket.transcription.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.init_transcription_func.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix="input/"
  }
  depends_on = [aws_lambda_permission.input_permissions]
}
 
resource "aws_lambda_permission" "input_permissions" {
  statement_id  = "AllowS3InvokeInput"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.init_transcription_func.arn
  principal = "s3.amazonaws.com"
  source_arn = aws_s3_bucket.transcription.arn
}

resource "aws_s3_bucket_notification" "output_file_trigger" {
  bucket = aws_s3_bucket.transcription.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.beautify_transcription_func.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix="output/"
  }
  depends_on = [aws_lambda_permission.output_permissions]
}
resource "aws_lambda_permission" "output_permissions" {
  statement_id  = "AllowS3InvokeOutput"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.beautify_transcription_func.arn
  principal = "s3.amazonaws.com"
  source_arn = aws_s3_bucket.transcription.arn
}
