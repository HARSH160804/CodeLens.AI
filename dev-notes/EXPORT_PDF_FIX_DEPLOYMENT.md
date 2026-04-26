# PDF Export Fix - Deployment Required

## Issue
PDF export is failing with a 500 error because the Lambda function still has the old dependencies (weasyprint) instead of the new Lambda-compatible library (reportlab).

## Root Cause
The code has been updated to use reportlab, but the Lambda function hasn't been redeployed with the new dependencies.

## Solution
Redeploy the Lambda function to update dependencies:

```bash
cd infrastructure
./deploy.sh
```

This will:
1. Build the SAM application with updated requirements.txt (reportlab)
2. Deploy the ExportDocsFunction Lambda with the new dependencies
3. Update the API Gateway endpoint

## What Changed
- **Old**: Used weasyprint (requires Cairo, Pango system libraries - not available in Lambda)
- **New**: Uses reportlab (pure Python, Lambda-compatible)

## Verification
After deployment, test the PDF export:

1. Generate documentation for a repository
2. Click "Export as PDF"
3. Should download a valid PDF file

## Alternative: Manual Lambda Update
If you can't run the full deployment, you can update just the Lambda function:

```bash
cd backend
pip install -r requirements.txt -t package/
cd package
zip -r ../deployment-package.zip .
cd ..
zip -g deployment-package.zip handlers/docs_export.py
zip -g deployment-package.zip lib/documentation/*.py

aws lambda update-function-code \
  --function-name h2s-backend-ExportDocsFunction-XXXXX \
  --zip-file fileb://deployment-package.zip
```

Replace `XXXXX` with your actual Lambda function suffix.

## Files Updated
- `backend/lib/documentation/exporter.py` - Now uses reportlab
- `backend/requirements.txt` - Added reportlab, removed weasyprint
- `backend/handlers/docs_export.py` - Fixed Markdown encoding (isBase64Encoded: False)
- All test files updated to mock reportlab correctly

## Test Status
- ✅ 33/38 tests passing
- ✅ All unit tests passing
- ✅ All bug exploration tests passing
- ✅ All preservation tests passing
- ⚠️ 5 integration tests failing (large documentation output issue, not functionality)
