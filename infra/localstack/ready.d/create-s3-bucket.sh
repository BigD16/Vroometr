#!/bin/bash
# Runs when LocalStack is ready. Bucket name comes from S3_BUCKET in .env.
set -euo pipefail

awslocal s3 mb "s3://${S3_BUCKET}" || true
awslocal s3 ls
