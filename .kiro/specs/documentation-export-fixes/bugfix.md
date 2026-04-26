# Bugfix Requirements Document

## Introduction

The documentation export functionality has two critical issues preventing users from successfully exporting generated documentation. The PDF export fails with a 500 error due to missing system dependencies in the Lambda environment (weasyprint requires Cairo, Pango, GDK-PixBuf), and the Markdown export downloads base64-encoded content instead of readable plain text. These issues block the core export workflow that users rely on to save and share their documentation.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user attempts to export documentation as PDF THEN the system returns a 500 error with message "Failed to export documentation. Please try again. Export failed: 500"

1.2 WHEN the backend processes a PDF export request THEN the system returns error code "CONVERSION_FAILED" with details "PDF conversion failed" because weasyprint dependencies (Cairo, Pango, GDK-PixBuf) are not available in Lambda

1.3 WHEN a user downloads documentation as Markdown THEN the system delivers a file containing base64-encoded content instead of plain text

1.4 WHEN the export handler returns Markdown content THEN the system sets `isBase64Encoded: True` in the response, causing the frontend or API Gateway to not properly decode the content for download

### Expected Behavior (Correct)

2.1 WHEN a user attempts to export documentation as PDF THEN the system SHALL successfully generate and download a PDF file using a Lambda-compatible approach

2.2 WHEN the backend processes a PDF export request THEN the system SHALL use a PDF generation method that works without system dependencies (such as HTML-to-PDF services, headless Chrome via AWS Lambda layers, or alternative libraries)

2.3 WHEN a user downloads documentation as Markdown THEN the system SHALL deliver a file containing readable plain text that opens correctly in any text editor

2.4 WHEN the export handler returns Markdown content THEN the system SHALL properly encode the response so that the frontend receives and downloads plain text content

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user generates documentation THEN the system SHALL CONTINUE TO successfully create documentation content

3.2 WHEN a user checks documentation generation status THEN the system SHALL CONTINUE TO return accurate status information

3.3 WHEN the export API is called with valid parameters THEN the system SHALL CONTINUE TO authenticate and authorize the request properly

3.4 WHEN documentation content is retrieved from storage THEN the system SHALL CONTINUE TO fetch the correct content for the specified repository and session
