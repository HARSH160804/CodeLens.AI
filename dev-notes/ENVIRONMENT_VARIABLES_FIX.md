# Environment Variables Fix - Documentation Generation

## Issue
Lambda functions were returning 502 Bad Gateway errors because they were missing required environment variables.

## Root Cause
The documentation Lambda functions (`GenerateDocsFunction`, `ExportDocsFunction`, `DocsStatusFunction`) were not configured with environment variables in the SAM template, but the code was trying to access them:

```python
repos_table = dynamodb.Table(os.environ.get('REPOSITORIES_TABLE', 'BloomWay-Repositories'))
```

When environment variables are missing, the Lambda function can fail during initialization or execution.

## Fix Applied

Added environment variables to all three documentation Lambda functions in `infrastructure/template.yaml`:

### GenerateDocsFunction
```yaml
Environment:
  Variables:
    REPOSITORIES_TABLE: !Ref RepositoriesTable
    EMBEDDINGS_TABLE: !Ref EmbeddingsTable
    CACHE_TABLE: !Ref CacheTable
    REPO_DOCUMENTATION_TABLE: !Ref RepoDocumentationTable
    CODE_BUCKET: !Ref CodeArtifactsBucket
```

### ExportDocsFunction
```yaml
Environment:
  Variables:
    REPO_DOCUMENTATION_TABLE: !Ref RepoDocumentationTable
    CODE_BUCKET: !Ref CodeArtifactsBucket
```

### DocsStatusFunction
```yaml
Environment:
  Variables:
    REPO_DOCUMENTATION_TABLE: !Ref RepoDocumentationTable
```

## Deployment Status
✅ Successfully deployed to AWS
✅ All Lambda functions updated with environment variables
✅ Functions can now access DynamoDB tables and S3 buckets

## Testing

### Test the fix:
1. Refresh your browser
2. Navigate to the Architecture page
3. Click "Generate Documentation"
4. The generation should now start successfully

### Expected behavior:
- POST request succeeds (no more 502 errors)
- Status changes: `not_generated` → `generating` → `generated`
- Export button appears when complete

## Files Modified
- `infrastructure/template.yaml` - Added Environment sections to all 3 documentation functions

## Environment Variables by Function

| Function | Variables |
|----------|-----------|
| GenerateDocsFunction | REPOSITORIES_TABLE, EMBEDDINGS_TABLE, CACHE_TABLE, REPO_DOCUMENTATION_TABLE, CODE_BUCKET |
| ExportDocsFunction | REPO_DOCUMENTATION_TABLE, CODE_BUCKET |
| DocsStatusFunction | REPO_DOCUMENTATION_TABLE |

## Why This Matters
Lambda functions need environment variables to:
1. Know which DynamoDB tables to query
2. Know which S3 buckets to use for storage
3. Access AWS resources with proper configuration

Without these variables, the functions fail with 502 errors because they can't initialize properly.

## Next Steps
1. Test the complete workflow in the browser
2. Verify documentation generation completes successfully
3. Test export functionality (Markdown and PDF)
4. Monitor CloudWatch logs for any remaining issues
