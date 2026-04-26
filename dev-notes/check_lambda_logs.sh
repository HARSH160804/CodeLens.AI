#!/bin/bash

# Check recent Lambda logs for documentation generation
FUNCTION_NAME="h2s-backend-GenerateDocsFunction-XE93G3N2AcGt"

echo "=== Checking Lambda Logs for $FUNCTION_NAME ==="
echo ""

# Get the log group name
LOG_GROUP="/aws/lambda/$FUNCTION_NAME"

echo "Fetching recent log streams..."
aws logs describe-log-streams \
  --log-group-name "$LOG_GROUP" \
  --order-by LastEventTime \
  --descending \
  --max-items 1 \
  --region us-east-1 \
  --query 'logStreams[0].logStreamName' \
  --output text > /tmp/latest_stream.txt

LATEST_STREAM=$(cat /tmp/latest_stream.txt)

if [ -z "$LATEST_STREAM" ] || [ "$LATEST_STREAM" = "None" ]; then
  echo "✗ No log streams found"
  exit 1
fi

echo "Latest stream: $LATEST_STREAM"
echo ""
echo "=== Recent Log Events ==="
aws logs get-log-events \
  --log-group-name "$LOG_GROUP" \
  --log-stream-name "$LATEST_STREAM" \
  --region us-east-1 \
  --limit 50 \
  --query 'events[*].message' \
  --output text

echo ""
echo "=== Done ==="
