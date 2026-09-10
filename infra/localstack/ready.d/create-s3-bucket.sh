#!/bin/bash
# Runs when LocalStack is ready. Bucket name comes from S3_BUCKET in .env.
set -euo pipefail

awslocal s3 mb "s3://${S3_BUCKET}" || true
awslocal s3api put-bucket-cors \
  --bucket "${S3_BUCKET}" \
  --cors-configuration '{
    "CORSRules": [
      {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["POST"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": ["ETag"],
        "MaxAgeSeconds": 300
      }
    ]
  }'
awslocal s3 ls
