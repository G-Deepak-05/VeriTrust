#!/bin/bash
# LocalStack initialization script
# Runs automatically when LocalStack is ready (via ready.d hook)
set -e

echo "==> Initializing LocalStack resources..."

# Create S3 bucket for verification documents
awslocal s3 mb s3://veritrust-docs --region us-east-1 2>/dev/null || echo "Bucket already exists"

# Set bucket versioning
awslocal s3api put-bucket-versioning \
  --bucket veritrust-docs \
  --versioning-configuration Status=Enabled

# Create SQS queue for async processing
awslocal sqs create-queue \
  --queue-name veritrust-events \
  --attributes '{"MessageRetentionPeriod":"86400","VisibilityTimeout":"60"}' 2>/dev/null || echo "Queue already exists"

# Create dead-letter queue
awslocal sqs create-queue \
  --queue-name veritrust-events-dlq \
  --attributes '{"MessageRetentionPeriod":"1209600"}' 2>/dev/null || echo "DLQ already exists"

echo "==> LocalStack initialization complete!"
echo "  S3 bucket: veritrust-docs"
echo "  SQS queue: veritrust-events"
echo "  SQS DLQ:   veritrust-events-dlq"
