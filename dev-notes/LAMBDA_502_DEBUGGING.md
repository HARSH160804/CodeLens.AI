# Lambda 502 Error Debugging Guide

## Current Status
The documentation generation Lambda is returning 502 errors, indicating the function is crashing before it can handle requests.

## Fixes Applied So Far

### 1. Added CORS OPTIONS handling ✅
### 2. Added environment variables ✅  
### 3. Fixed environment variable name mismatch ✅
### 4. Changed to lazy initialization ✅

## Still Getting 502 Errors

The Lambda function is still crashing. This suggests one of the following:

### Possible Causes

1. **Import Error** - One of the imported modules is failing to load
   - `lib.bedrock_client`
   - `lib.documentation.store`
   - `lib.documentation.generator`
   - `lib.analysis.engine`
   - `lib.analysis.cache_manager`

2. **Missing Dependencies** - Required Python packages not in requirements.txt
   - Check if all imports are available in the Lambda environment

3. **Initialization Error** - Even with lazy loading, something is failing at module load time

## Next Steps to Debug

### Option 1: Check CloudWatch Logs
```bash
aws logs tail /aws/lambda/h2s-backend-GenerateDocsFunction-XE93G3N2AcGt --follow
```

### Option 2: Create Minimal Test Handler
Create a simple handler that just returns success to verify the Lambda works:

```python
def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'message': 'Test successful'})
    }
```

### Option 3: Add Try-Catch Around Imports
Wrap imports in try-catch to see which one is failing:

```python
try:
    from lib.bedrock_client import BedrockClient
    logger.info("BedrockClient imported successfully")
except Exception as e:
    logger.error(f"Failed to import BedrockClient: {e}")
```

### Option 4: Check Lambda Execution Role
Verify the Lambda has permissions to:
- Access DynamoDB tables
- Access S3 buckets
- Invoke Bedrock models
- Write to CloudWatch Logs

## Recommended Action

Check CloudWatch Logs to see the actual error message. The logs will show:
- Import errors
- Initialization errors
- Permission errors
- Any exceptions thrown during module load

Command to view logs:
```bash
aws logs tail /aws/lambda/h2s-backend-GenerateDocsFunction-XE93G3N2AcGt --since 5m
```

Look for:
- `ImportError`
- `ModuleNotFoundError`
- `AttributeError`
- `PermissionError`
- Any stack traces

## Temporary Workaround

If the issue persists, consider:
1. Simplifying the handler to just update DynamoDB state
2. Moving the actual generation to a separate async process
3. Using Step Functions to orchestrate the workflow
4. Breaking down the monolithic handler into smaller functions
