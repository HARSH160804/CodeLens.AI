# Async Repository Ingestion - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying, configuring, monitoring, and troubleshooting the async repository ingestion system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Steps](#deployment-steps)
3. [Environment Configuration](#environment-configuration)
4. [Verification](#verification)
5. [Monitoring Setup](#monitoring-setup)
6. [Operational Runbook](#operational-runbook)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

- AWS CLI v2.x or higher
- AWS SAM CLI v1.x or higher
- Python 3.9
- Git
- jq (for JSON parsing in scripts)

### AWS Account Requirements

- AWS Account with appropriate permissions
- IAM permissions for:
  - Lambda (create, update, delete functions)
  - DynamoDB (create, update tables)
  - SQS (create, configure queues)
  - S3 (create, manage buckets)
  - CloudWatch (create alarms, view logs)
  - API Gateway (create, update APIs)
  - IAM (create, attach roles and policies)

### Account Limits

Verify your account has sufficient limits:

```bash
# Check Lambda concurrent execution limit
aws lambda get-account-settings

# Check DynamoDB table limit
aws service-quotas get-service-quota \
  --service-code dynamodb \
  --quota-code L-F98FE922
```

---

## Deployment Steps

### 1. Clone Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Install Dependencies

```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt
cd ..
```

### 3. Configure SAM

Edit `infrastructure/samconfig.toml`:

```toml
[default.deploy.parameters]
stack_name = "h2s-backend"
region = "us-east-1"
capabilities = "CAPABILITY_IAM"
confirm_changeset = true
```

### 4. Build SAM Application

```bash
cd infrastructure
sam build
```

Expected output:
```
Build Succeeded

Built Artifacts  : .aws-sam/build
Built Template   : .aws-sam/build/template.yaml
```

### 5. Deploy to AWS

```bash
sam deploy
```

Review the changeset and confirm deployment.

### 6. Capture Outputs

```bash
# Get API endpoint
aws cloudformation describe-stacks \
  --stack-name h2s-backend \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text

# Save to environment variable
export API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name h2s-backend \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)
```

---

## Environment Configuration

### Lambda Environment Variables

All Lambda functions automatically receive these environment variables from the SAM template:

#### Global Variables (All Functions)

- `SESSIONS_TABLE`: DynamoDB sessions table name
- `REPOSITORIES_TABLE`: DynamoDB repositories table name
- `EMBEDDINGS_TABLE`: DynamoDB embeddings table name
- `CODE_BUCKET`: S3 bucket for code artifacts
- `CACHE_TABLE`: DynamoDB cache table name
- `DOCS_TABLE`: DynamoDB documentation table name
- `INGESTION_JOBS_TABLE`: DynamoDB ingestion jobs table name
- `PROCESSING_QUEUE_URL`: SQS processing queue URL
- `BEDROCK_REGION`: AWS region for Bedrock API

#### Function-Specific Variables

No additional configuration required - all variables are set via SAM template.

### Frontend Configuration

Update `frontend/.env`:

```bash
VITE_API_ENDPOINT=https://<api-id>.execute-api.us-east-1.amazonaws.com/Prod
```

---

## Verification

### 1. Verify Infrastructure

```bash
# Check all resources exist
aws cloudformation describe-stack-resources \
  --stack-name h2s-backend \
  --query 'StackResources[*].[LogicalResourceId,ResourceType,ResourceStatus]' \
  --output table
```

Expected resources:
- ✅ IngestAsyncFunction (AWS::Serverless::Function)
- ✅ ProcessRepoWorkerFunction (AWS::Serverless::Function)
- ✅ GetIngestionStatusFunction (AWS::Serverless::Function)
- ✅ IngestionJobsTable (AWS::DynamoDB::Table)
- ✅ ProcessingQueue (AWS::SQS::Queue)
- ✅ ProcessingDLQ (AWS::SQS::Queue)
- ✅ ProcessingErrorAlarm (AWS::CloudWatch::Alarm)
- ✅ DLQMessagesAlarm (AWS::CloudWatch::Alarm)

### 2. Test Async Ingestion Endpoint

```bash
# Test with small repository
curl -X POST $API_ENDPOINT/repos/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "github",
    "source": "https://github.com/octocat/Hello-World"
  }'
```

Expected response:
```json
{
  "job_id": "uuid-here",
  "status": "processing",
  "progress_current": 0,
  "progress_total": 0,
  "created_at": "2026-03-06T12:00:00Z",
  "updated_at": "2026-03-06T12:00:00Z"
}
```

### 3. Test Status Endpoint

```bash
# Replace JOB_ID with actual job_id from previous response
JOB_ID="<job-id-from-response>"
curl $API_ENDPOINT/ingestion/status/$JOB_ID
```

Expected response:
```json
{
  "job_id": "uuid-here",
  "status": "processing",
  "progress_current": 5,
  "progress_total": 10,
  "created_at": "2026-03-06T12:00:00Z",
  "updated_at": "2026-03-06T12:00:05Z"
}
```

### 4. Verify SQS Integration

```bash
# Check queue has messages
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name BloomWay-RepositoryProcessing --query 'QueueUrl' --output text) \
  --attribute-names ApproximateNumberOfMessages
```

### 5. Verify Worker Processing

```bash
# Watch worker logs
aws logs tail /aws/lambda/ProcessRepoWorkerFunction --follow
```

Look for:
- ✅ "Processing job: <job_id>"
- ✅ "Progress: X/Y files"
- ✅ "Job completed successfully"

---

## Monitoring Setup

### CloudWatch Dashboards

Create a custom dashboard:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name BloomWay-AsyncIngestion \
  --dashboard-body file://monitoring/dashboard.json
```

Dashboard includes:
- Jobs started per hour
- Jobs completed per hour
- Jobs failed per hour
- Average processing duration
- Worker error rate
- DLQ message count
- Lambda memory usage
- Lambda duration

### CloudWatch Alarms

Already configured via SAM template:

1. **ProcessingErrorAlarm**
   - Metric: Lambda Errors
   - Threshold: > 10 errors in 5 minutes
   - Action: SNS notification (configure SNS topic)

2. **DLQMessagesAlarm**
   - Metric: SQS ApproximateNumberOfMessagesVisible
   - Threshold: >= 1 message
   - Action: SNS notification (configure SNS topic)

### Configure SNS Notifications

```bash
# Create SNS topic
aws sns create-topic --name BloomWay-Alerts

# Subscribe email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:<account-id>:BloomWay-Alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Update alarms to use SNS topic
aws cloudwatch put-metric-alarm \
  --alarm-name BloomWay-ProcessingWorker-HighErrorRate \
  --alarm-actions arn:aws:sns:us-east-1:<account-id>:BloomWay-Alerts

aws cloudwatch put-metric-alarm \
  --alarm-name BloomWay-ProcessingDLQ-MessagesPresent \
  --alarm-actions arn:aws:sns:us-east-1:<account-id>:BloomWay-Alerts
```

### Log Insights Queries

#### Query 1: Failed Jobs

```sql
fields @timestamp, job_id, error_message
| filter status = "failed"
| sort @timestamp desc
| limit 20
```

#### Query 2: Processing Duration

```sql
fields @timestamp, job_id, duration_ms
| filter status = "completed"
| stats avg(duration_ms), max(duration_ms), min(duration_ms)
```

#### Query 3: Memory Usage

```sql
fields @timestamp, @maxMemoryUsed / 1000000 as memory_mb
| filter @type = "REPORT"
| stats avg(memory_mb), max(memory_mb)
```

---

## Operational Runbook

### Common Operations

#### 1. Check System Health

```bash
# Check all Lambda functions
aws lambda list-functions \
  --query 'Functions[?contains(FunctionName, `BloomWay`)].FunctionName'

# Check DynamoDB tables
aws dynamodb list-tables \
  --query 'TableNames[?contains(@, `BloomWay`)]'

# Check SQS queues
aws sqs list-queues \
  --queue-name-prefix BloomWay
```

#### 2. Monitor Active Jobs

```bash
# Scan for processing jobs
aws dynamodb scan \
  --table-name BloomWay-IngestionJobs \
  --filter-expression "job_status = :status" \
  --expression-attribute-values '{":status":{"S":"processing"}}' \
  --projection-expression "job_id,created_at,progress_current,progress_total"
```

#### 3. Check Queue Depth

```bash
# Get queue metrics
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name BloomWay-RepositoryProcessing --query 'QueueUrl' --output text) \
  --attribute-names All
```

#### 4. View Recent Errors

```bash
# Query CloudWatch Logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/ProcessRepoWorkerFunction \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

#### 5. Manually Retry Failed Job

```bash
# Get failed job details
aws dynamodb get-item \
  --table-name BloomWay-IngestionJobs \
  --key '{"job_id":{"S":"<job-id>"}}'

# Re-enqueue to SQS
aws sqs send-message \
  --queue-url $(aws sqs get-queue-url --queue-name BloomWay-RepositoryProcessing --query 'QueueUrl' --output text) \
  --message-body '{"job_id":"<job-id>","source_type":"github","source":"<repo-url>"}'
```

#### 6. Pause Processing

```bash
# Disable SQS event source
EVENT_UUID=$(aws lambda list-event-source-mappings \
  --function-name ProcessRepoWorkerFunction \
  --query 'EventSourceMappings[0].UUID' \
  --output text)

aws lambda update-event-source-mapping \
  --uuid $EVENT_UUID \
  --enabled false
```

#### 7. Resume Processing

```bash
# Enable SQS event source
aws lambda update-event-source-mapping \
  --uuid $EVENT_UUID \
  --enabled true
```

#### 8. Purge Queue (Emergency)

```bash
# WARNING: This deletes all pending jobs
aws sqs purge-queue \
  --queue-url $(aws sqs get-queue-url --queue-name BloomWay-RepositoryProcessing --query 'QueueUrl' --output text)
```

---

## Rollback Procedures

### Scenario 1: Async Endpoint Issues

**Symptoms**: Async ingestion failing, but sync ingestion works

**Solution**: Re-enable legacy sync endpoint

```bash
# Edit infrastructure/template.yaml
# Add Events section to IngestRepoFunctionLegacy:
#   Events:
#     IngestRepo:
#       Type: Api
#       Properties:
#         RestApiId: !Ref BloomWayApi
#         Path: /repos/ingest
#         Method: POST

# Remove Events section from IngestAsyncFunction

# Deploy
sam build && sam deploy
```

### Scenario 2: Worker Function Issues

**Symptoms**: Jobs stuck in processing, worker errors

**Solution**: Pause processing and rollback

```bash
# 1. Pause processing
EVENT_UUID=$(aws lambda list-event-source-mappings \
  --function-name ProcessRepoWorkerFunction \
  --query 'EventSourceMappings[0].UUID' \
  --output text)

aws lambda update-event-source-mapping \
  --uuid $EVENT_UUID \
  --enabled false

# 2. Rollback to previous version
git checkout <previous-commit>
sam build && sam deploy

# 3. Resume processing
aws lambda update-event-source-mapping \
  --uuid $EVENT_UUID \
  --enabled true
```

### Scenario 3: Complete Rollback

**Symptoms**: System-wide issues

**Solution**: Full stack rollback

```bash
# 1. Pause all processing
aws lambda update-event-source-mapping \
  --uuid $EVENT_UUID \
  --enabled false

# 2. Rollback code
git checkout <previous-stable-commit>

# 3. Deploy previous version
sam build && sam deploy

# 4. Verify rollback
curl $API_ENDPOINT/repos/<repo-id>/status

# 5. Resume if successful
aws lambda update-event-source-mapping \
  --uuid $EVENT_UUID \
  --enabled true
```

### Scenario 4: Data Corruption

**Symptoms**: Invalid data in DynamoDB or embeddings

**Solution**: Clean up and re-process

```bash
# 1. Identify affected jobs
aws dynamodb scan \
  --table-name BloomWay-IngestionJobs \
  --filter-expression "created_at > :timestamp" \
  --expression-attribute-values '{":timestamp":{"S":"2026-03-06T00:00:00Z"}}'

# 2. Delete corrupted embeddings
aws dynamodb delete-item \
  --table-name BloomWay-Embeddings \
  --key '{"repo_id":{"S":"<repo-id>"},"chunk_id":{"S":"<chunk-id>"}}'

# 3. Reset job status
aws dynamodb update-item \
  --table-name BloomWay-IngestionJobs \
  --key '{"job_id":{"S":"<job-id>"}}' \
  --update-expression "SET job_status = :status" \
  --expression-attribute-values '{":status":{"S":"pending"}}'

# 4. Re-enqueue
aws sqs send-message \
  --queue-url $(aws sqs get-queue-url --queue-name BloomWay-RepositoryProcessing --query 'QueueUrl' --output text) \
  --message-body '{"job_id":"<job-id>"}'
```

---

## Troubleshooting

### Issue 1: Jobs Stuck in Processing

**Symptoms**:
- Job status remains "processing" for > 15 minutes
- No progress updates

**Diagnosis**:
```bash
# Check worker logs
aws logs tail /aws/lambda/ProcessRepoWorkerFunction --since 15m

# Check if worker is running
aws lambda get-function \
  --function-name ProcessRepoWorkerFunction \
  --query 'Configuration.State'
```

**Solutions**:

1. **Stale job detection should auto-fail** - Wait for next worker invocation
2. **Manually fail job**:
   ```bash
   aws dynamodb update-item \
     --table-name BloomWay-IngestionJobs \
     --key '{"job_id":{"S":"<job-id>"}}' \
     --update-expression "SET job_status = :status, error_message = :error" \
     --expression-attribute-values '{":status":{"S":"failed"},":error":{"S":"Manual intervention - timeout"}}'
   ```

### Issue 2: High Error Rate

**Symptoms**:
- ProcessingErrorAlarm triggered
- Many jobs failing

**Diagnosis**:
```bash
# Check error patterns
aws logs filter-log-events \
  --log-group-name /aws/lambda/ProcessRepoWorkerFunction \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  | jq '.events[].message'
```

**Solutions**:

1. **Bedrock throttling**: Increase retry backoff
2. **Memory issues**: Increase Lambda memory
3. **Timeout issues**: Increase Lambda timeout
4. **Invalid input**: Add validation to ingestion endpoint

### Issue 3: DLQ Messages

**Symptoms**:
- DLQMessagesAlarm triggered
- Messages in dead letter queue

**Diagnosis**:
```bash
# Receive messages from DLQ
aws sqs receive-message \
  --queue-url $(aws sqs get-queue-url --queue-name BloomWay-RepositoryProcessing-DLQ --query 'QueueUrl' --output text) \
  --max-number-of-messages 10
```

**Solutions**:

1. **Analyze failure reason** from message attributes
2. **Fix underlying issue** (code bug, config error)
3. **Manually re-process**:
   ```bash
   # Move message back to main queue
   aws sqs send-message \
     --queue-url $(aws sqs get-queue-url --queue-name BloomWay-RepositoryProcessing --query 'QueueUrl' --output text) \
     --message-body '<message-body-from-dlq>'
   ```

### Issue 4: Out of Memory

**Symptoms**:
- Worker fails with "Runtime exited with error: signal: killed"
- Memory usage near 3008 MB

**Diagnosis**:
```bash
# Check memory usage
aws logs filter-log-events \
  --log-group-name /aws/lambda/ProcessRepoWorkerFunction \
  --filter-pattern "REPORT" \
  | jq '.events[].message' \
  | grep "Max Memory Used"
```

**Solutions**:

1. **Reduce batch size** in worker (currently 50 files)
2. **Increase Lambda memory** to 4096 MB or 5120 MB
3. **Add more aggressive GC** between batches

### Issue 5: Slow Processing

**Symptoms**:
- Jobs taking > 10 minutes for small repos
- High Lambda duration

**Diagnosis**:
```bash
# Check average duration
aws logs filter-log-events \
  --log-group-name /aws/lambda/ProcessRepoWorkerFunction \
  --filter-pattern "REPORT" \
  | jq '.events[].message' \
  | grep "Duration"
```

**Solutions**:

1. **Check Bedrock latency** - may need to switch regions
2. **Optimize batch processing** - increase batch size
3. **Add caching** for repeated embeddings
4. **Increase Lambda memory** (more CPU allocated)

### Issue 6: Idempotency Not Working

**Symptoms**:
- Same repository processed multiple times
- Duplicate embeddings

**Diagnosis**:
```bash
# Check for duplicate jobs
aws dynamodb query \
  --table-name BloomWay-IngestionJobs \
  --index-name idempotency-index \
  --key-condition-expression "idempotency_key = :key" \
  --expression-attribute-values '{":key":{"S":"<sha256-hash>"}}'
```

**Solutions**:

1. **Verify idempotency key generation** - check hash algorithm
2. **Check GSI status** - ensure index is active
3. **Add logging** to idempotency checks

---

## Performance Tuning

### Lambda Configuration

Current settings:
- IngestAsyncFunction: 512 MB, 30s timeout
- ProcessRepoWorkerFunction: 3008 MB, 900s timeout
- GetIngestionStatusFunction: 256 MB, 10s timeout

Tuning recommendations:

1. **For large repos (> 500 files)**:
   - Increase worker memory to 4096 MB
   - Increase timeout to 900s (max)

2. **For high throughput**:
   - Increase SQS batch size (currently 1)
   - Add reserved concurrency to worker

3. **For cost optimization**:
   - Reduce worker memory if usage < 2GB
   - Enable Lambda SnapStart (Python 3.9+)

### DynamoDB Configuration

Current settings:
- Billing mode: PAY_PER_REQUEST
- No provisioned capacity

Tuning recommendations:

1. **For predictable workload**:
   - Switch to provisioned capacity
   - Enable auto-scaling

2. **For cost optimization**:
   - Reduce TTL to 3 days (currently 7)
   - Archive old jobs to S3

### SQS Configuration

Current settings:
- Visibility timeout: 900s
- Message retention: 4 days
- Max receive count: 3

Tuning recommendations:

1. **For faster retries**:
   - Reduce visibility timeout to 600s
   - Increase max receive count to 5

2. **For reliability**:
   - Increase message retention to 7 days
   - Add delay queue for rate limiting

---

## Cost Optimization

### Current Cost Breakdown (per 1000 repos)

- Lambda: ~$9
- DynamoDB: ~$0.25
- SQS: ~$0.0004
- Bedrock: ~$10
- **Total**: ~$19/1000 repos

### Optimization Strategies

1. **Reduce Lambda costs**:
   - Use ARM architecture (already enabled)
   - Optimize memory allocation
   - Enable SnapStart

2. **Reduce DynamoDB costs**:
   - Use provisioned capacity for predictable load
   - Reduce TTL duration
   - Archive old data to S3

3. **Reduce Bedrock costs**:
   - Cache embeddings for common code patterns
   - Use smaller embedding models
   - Batch embedding requests

4. **Reduce S3 costs**:
   - Enable lifecycle policies (already enabled)
   - Use Intelligent-Tiering
   - Compress artifacts

---

## Security Best Practices

### IAM Policies

- ✅ Least privilege access for all Lambda functions
- ✅ No wildcard permissions
- ✅ Resource-specific policies

### Encryption

- ✅ DynamoDB encryption at rest (SSE)
- ✅ S3 encryption at rest (AES256)
- ✅ SQS encryption in transit (HTTPS)

### Network Security

- ✅ API Gateway CORS configured
- ✅ S3 bucket public access blocked
- ✅ Lambda in VPC (optional, not currently enabled)

### Monitoring

- ✅ CloudWatch Logs enabled
- ✅ CloudWatch Alarms configured
- ✅ DynamoDB streams enabled

---

## Maintenance Schedule

### Daily

- Check CloudWatch alarms
- Review error logs
- Monitor queue depth

### Weekly

- Review cost reports
- Analyze performance metrics
- Check DLQ for stuck messages

### Monthly

- Review and update IAM policies
- Optimize Lambda memory allocation
- Archive old DynamoDB records
- Update dependencies

### Quarterly

- Review security posture
- Update documentation
- Conduct disaster recovery drill
- Review and optimize costs

---

## Support and Escalation

### Level 1: Self-Service

- Check this documentation
- Review CloudWatch Logs
- Check AWS Service Health Dashboard

### Level 2: Team Support

- Contact development team
- Provide job_id and error logs
- Include CloudWatch Insights query results

### Level 3: AWS Support

- Open AWS Support case
- Provide stack name and region
- Include CloudFormation template
- Attach relevant logs

---

## Appendix

### A. Useful Scripts

#### Script 1: Health Check

```bash
#!/bin/bash
# health_check.sh

echo "=== BloomWay Async Ingestion Health Check ==="

# Check Lambda functions
echo "Checking Lambda functions..."
aws lambda list-functions \
  --query 'Functions[?contains(FunctionName, `BloomWay`)].{Name:FunctionName,State:State}' \
  --output table

# Check DynamoDB tables
echo "Checking DynamoDB tables..."
aws dynamodb list-tables \
  --query 'TableNames[?contains(@, `BloomWay`)]' \
  --output table

# Check SQS queues
echo "Checking SQS queues..."
aws sqs list-queues \
  --queue-name-prefix BloomWay \
  --output table

# Check CloudWatch alarms
echo "Checking CloudWatch alarms..."
aws cloudwatch describe-alarms \
  --alarm-name-prefix BloomWay \
  --query 'MetricAlarms[*].{Name:AlarmName,State:StateValue}' \
  --output table

echo "=== Health Check Complete ==="
```

#### Script 2: Job Status Monitor

```bash
#!/bin/bash
# monitor_jobs.sh

JOB_ID=$1

if [ -z "$JOB_ID" ]; then
  echo "Usage: ./monitor_jobs.sh <job-id>"
  exit 1
fi

API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name h2s-backend \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

while true; do
  clear
  echo "=== Job Status: $JOB_ID ==="
  curl -s $API_ENDPOINT/ingestion/status/$JOB_ID | jq '.'
  
  STATUS=$(curl -s $API_ENDPOINT/ingestion/status/$JOB_ID | jq -r '.status')
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    echo "Job finished with status: $STATUS"
    break
  fi
  
  sleep 2
done
```

### B. CloudWatch Dashboard JSON

See `monitoring/dashboard.json` for complete dashboard configuration.

### C. Useful AWS CLI Commands

```bash
# Get all stack outputs
aws cloudformation describe-stacks \
  --stack-name h2s-backend \
  --query 'Stacks[0].Outputs'

# Get Lambda function configuration
aws lambda get-function-configuration \
  --function-name ProcessRepoWorkerFunction

# Get DynamoDB table description
aws dynamodb describe-table \
  --table-name BloomWay-IngestionJobs

# Get SQS queue attributes
aws sqs get-queue-attributes \
  --queue-url <queue-url> \
  --attribute-names All

# Tail Lambda logs
aws logs tail /aws/lambda/ProcessRepoWorkerFunction --follow

# Query logs with filter
aws logs filter-log-events \
  --log-group-name /aws/lambda/ProcessRepoWorkerFunction \
  --filter-pattern "ERROR"
```

---

## Conclusion

This deployment guide provides comprehensive instructions for deploying, configuring, monitoring, and troubleshooting the async repository ingestion system. Follow the procedures carefully and refer to the troubleshooting section for common issues.

For additional support, contact the development team or open an AWS Support case.

**Last Updated**: March 6, 2026
**Version**: 1.0.0
