# Design Document: Documentation Generation and Export Workflow

## Overview

This design establishes a stateful documentation generation and export workflow that separates documentation creation from format conversion. The system leverages existing architecture analysis data from the AnalysisEngine to generate comprehensive technical documentation once, stores it persistently, and enables on-demand export in multiple formats (Markdown and PDF).

The key architectural principle is separation of concerns: the AnalysisEngine performs repository analysis and produces structured JSON data, the DocumentationGenerator consumes this data to create formatted documentation using AI, the DocumentationStore persists the generated content, and the ExportService handles format conversion and delivery.

This approach eliminates redundant AI calls, improves performance, reduces costs, and provides a better user experience with clear state management and preview capabilities.

## Architecture

### System Components

The documentation workflow consists of four primary components:

1. **AnalysisEngine** (existing): Analyzes repositories and produces structured JSON containing patterns, layers, components, tech stack, dependencies, data flows, metrics, recommendations, and visualizations.

2. **DocumentationGenerator** (new): Consumes AnalysisEngine JSON output and uses AI (Bedrock) to generate comprehensive markdown documentation with proper formatting, narrative flow, and technical depth.

3. **DocumentationStore** (new): Persistent storage layer using DynamoDB to store generated documentation with metadata (repo_id, creation_timestamp, content_hash, generation_state).

4. **ExportService** (new): Retrieves stored documentation and converts it to requested formats (markdown passthrough, PDF via markdown→HTML→PDF pipeline).

### Data Flow

```
User Request → Architecture Page
    ↓
Check Generation State (DynamoDB)
    ↓
[If not_generated] → Generate Button → POST /repos/{id}/docs/generate
    ↓
Retrieve Analysis Data (from /architecture endpoint or cache)
    ↓
DocumentationGenerator (AI formatting)
    ↓
Store Markdown (DynamoDB)
    ↓
Update State to 'generated'
    ↓
[If generated] → Export Dropdown → GET /repos/{id}/docs/export?format=md|pdf
    ↓
Retrieve Stored Markdown (DynamoDB)
    ↓
[If PDF] → Convert: Markdown → HTML → PDF (weasyprint)
    ↓
Return File for Download
```

### State Machine

Documentation generation follows a state machine with four states:

- **not_generated**: Initial state, no documentation exists
- **generating**: Generation in progress (async operation)
- **generated**: Documentation successfully created and stored
- **failed**: Generation failed, error logged

State transitions:
- not_generated → generating (on generate request)
- generating → generated (on success)
- generating → failed (on error)
- generated → generating (on regenerate request)
- failed → generating (on retry/regenerate)

## Components and Interfaces

### 1. DocumentationGenerator

**Purpose**: Transform structured analysis data into comprehensive markdown documentation using AI.

**Interface**:
```python
class DocumentationGenerator:
    def __init__(self, bedrock_client: BedrockClient):
        """Initialize with Bedrock client for AI generation."""
        
    async def generate(self, analysis_data: Dict[str, Any]) -> str:
        """
        Generate markdown documentation from analysis data.
        
        Args:
            analysis_data: Complete ArchitectureAnalysis JSON from AnalysisEngine
            
        Returns:
            Formatted markdown string
            
        Raises:
            GenerationError: If AI generation fails
            ValidationError: If analysis_data is incomplete
        """
```

**Implementation Details**:
- Accepts ArchitectureAnalysis JSON structure (see architecture_models.py)
- Uses Bedrock Claude model for natural language generation
- Generates sections: Overview, Architecture Patterns, Layers & Components, Tech Stack, Data Flows, Dependencies, Quality Metrics, Recommendations
- Includes Mermaid diagrams from visualizations field
- Validates output markdown structure before returning
- Does NOT re-analyze code (uses provided data only)

### 2. DocumentationStore

**Purpose**: Persist generated documentation with metadata for fast retrieval.

**DynamoDB Schema**:
```
Table: RepoDocumentation
Primary Key: repo_id (String)
Attributes:
  - repo_id: String (partition key)
  - content: String (markdown content, potentially large)
  - content_hash: String (SHA256 of content)
  - generation_state: String (not_generated|generating|generated|failed)
  - created_at: String (ISO 8601 timestamp)
  - updated_at: String (ISO 8601 timestamp)
  - error_message: String (optional, present if state=failed)
  - metadata: Map (optional, for future extensions)
```

**Interface**:
```python
class DocumentationStore:
    async def save(self, repo_id: str, content: str) -> None:
        """Save generated documentation."""
        
    async def get(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve documentation with metadata."""
        
    async def get_state(self, repo_id: str) -> str:
        """Get current generation state."""
        
    async def update_state(self, repo_id: str, state: str, error: str = None) -> None:
        """Update generation state atomically."""
        
    async def delete(self, repo_id: str) -> None:
        """Delete documentation (for cleanup)."""
```

**Implementation Details**:
- Uses DynamoDB for persistence (fast reads, scalable)
- Stores markdown content directly (DynamoDB supports up to 400KB items)
- For larger documents (>400KB), stores content in S3 and reference in DynamoDB
- Implements atomic state updates using conditional writes
- Calculates content_hash for change detection

### 3. ExportService

**Purpose**: Convert stored documentation to requested formats and deliver for download.

**Interface**:
```python
class ExportService:
    def __init__(self, store: DocumentationStore):
        """Initialize with documentation store."""
        
    async def export_markdown(self, repo_id: str) -> bytes:
        """
        Export documentation as markdown.
        
        Returns:
            Raw markdown bytes for download
            
        Raises:
            NotFoundError: If documentation doesn't exist
        """
        
    async def export_pdf(self, repo_id: str) -> bytes:
        """
        Export documentation as PDF.
        
        Returns:
            PDF bytes for download
            
        Raises:
            NotFoundError: If documentation doesn't exist
            ConversionError: If PDF conversion fails
        """
```

**PDF Conversion Pipeline**:
1. Retrieve markdown from store
2. Convert markdown to HTML using `markdown` library with extensions (tables, fenced_code, toc)
3. Apply CSS styling (readable fonts, proper margins, code block formatting)
4. Convert HTML to PDF using `weasyprint` library
5. Cache PDF in memory for 1 hour (using TTL cache)
6. Return PDF bytes

**Implementation Details**:
- Markdown export: simple passthrough from store
- PDF conversion uses weasyprint (pure Python, no external dependencies)
- CSS template includes: page margins, font families, code block styling, table of contents
- Implements caching to avoid repeated conversions
- Handles large documents with streaming if needed

### 4. API Handlers

**POST /repos/{id}/docs/generate**
```python
async def generate_handler(event, context):
    """
    Trigger documentation generation.
    
    Request: POST /repos/{repo_id}/docs/generate
    Response: 202 Accepted
    {
        "status": "generating",
        "message": "Documentation generation started"
    }
    """
```

**GET /repos/{id}/docs/export**
```python
async def export_handler(event, context):
    """
    Export documentation in requested format.
    
    Request: GET /repos/{repo_id}/docs/export?format=md|pdf
    Response: 200 OK with file download
    Headers:
        Content-Type: text/markdown or application/pdf
        Content-Disposition: attachment; filename="repo-docs.{ext}"
    """
```

**GET /repos/{id}/docs/status**
```python
async def status_handler(event, context):
    """
    Get documentation generation status.
    
    Request: GET /repos/{repo_id}/docs/status
    Response: 200 OK
    {
        "state": "generated|generating|not_generated|failed",
        "created_at": "2024-01-15T10:30:00Z",
        "error_message": "..." (if failed)
    }
    """
```

### 5. Frontend Components

**ArchitecturePage Updates**:
- Add state management for documentation generation state
- Conditionally render Generate button or Export dropdown based on state
- Show loading indicator during generation
- Handle error states with user-friendly messages

**DocumentationPreview Component** (new):
- Modal or full-page view displaying rendered markdown
- Uses react-markdown for rendering
- Provides export actions (Download Markdown, Download PDF)
- Shows creation timestamp
- Includes close/back action

## Data Models

### ArchitectureAnalysis Input

The DocumentationGenerator receives the complete ArchitectureAnalysis structure from the AnalysisEngine (defined in architecture_models.py):

```python
@dataclass
class ArchitectureAnalysis:
    schema_version: str
    repo_id: str
    generated_at: str
    execution_duration_ms: int
    analysis_level: str
    statistics: CodebaseStatistics
    patterns: List[DetectedPattern]
    layers: List[Layer]
    tech_stack: List[Technology]
    data_flows: List[DataFlowScenario]
    dependencies: DependencyAnalysis
    metrics: QualityMetrics
    recommendations: List[Recommendation]
    visualizations: Dict[str, Visualization]
    architecture: LegacyArchitecture
    diagram: str
```

### Documentation Output Structure

Generated markdown follows this structure:

```markdown
# Repository Documentation

## Overview
[AI-generated summary of repository purpose and architecture]

## Architecture Patterns
[Description of detected patterns with confidence scores]

### Pattern: {name}
- Confidence: {confidence}
- Evidence: {evidence_files}
- Description: {description}
- Pros: {pros}
- Cons: {cons}

## Layers and Components

### {layer_name}
[Description of layer]

#### Components
- {component_name} ({type}): {responsibilities}
  - File: {file_path}
  - Complexity: {complexity_score}
  - Health: {health_score}

## Technology Stack

### {category}
- {name} {version}: {description}
  [Vulnerabilities if any]

## Data Flows

### {scenario_name}
[Description]

```mermaid
{mermaid_diagram}
```

[Flow steps]

## Dependencies

### Dependency Tree
[Visualization and analysis]

### Issues
- Circular Dependencies: {count}
- Outdated Packages: {count}
- Vulnerabilities: {count}

## Quality Metrics

### Health Score: {score}/100

### Complexity Metrics
- Average Cyclomatic: {value}
- Average Cognitive: {value}

### Hotspots
[List of code hotspots with recommendations]

### Technical Debt
- Code Duplication: {percentage}%
- Estimated Debt: {hours} hours

## Recommendations

### {category} - {priority}
**{title}**

{description}

- Effort: {estimated_effort}
- Impact: {expected_impact}
- Files: {file_paths}

---
Generated: {timestamp}
```

### DocumentationRecord Model

```python
@dataclass
class DocumentationRecord:
    repo_id: str
    content: str
    content_hash: str
    generation_state: str
    created_at: str
    updated_at: str
    error_message: Optional[str] = None
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Complete Documentation Structure

*For any* valid ArchitectureAnalysis data, the generated documentation SHALL contain all required sections: Overview, Architecture Patterns, Layers and Components, Technology Stack, Data Flows, Dependencies, Quality Metrics, and Recommendations.

**Validates: Requirements 1.1, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7**

### Property 2: Data Fidelity

*For any* ArchitectureAnalysis data provided to the DocumentationGenerator, the generated documentation SHALL contain information derived from that data and SHALL NOT contain information from external analysis or re-analysis.

**Validates: Requirements 1.2**

### Property 3: Valid Markdown Output

*For any* generated documentation, the output SHALL be valid markdown syntax that can be parsed without errors.

**Validates: Requirements 7.8**

### Property 4: Storage Round-Trip

*For any* generated documentation content, storing it with a repository ID and then retrieving it by that repository ID SHALL return the same content along with all required metadata (creation timestamp, content hash).

**Validates: Requirements 2.1, 2.2, 2.3**

### Property 5: State Persistence

*For any* repository with generated documentation, the Generation_State SHALL remain 'generated' across multiple status queries until explicitly changed by regeneration or deletion.

**Validates: Requirements 2.3, 2.5**

### Property 6: Latest Version Retrieval

*For any* repository where documentation is generated multiple times, retrieving documentation SHALL always return the most recently generated version based on creation timestamp.

**Validates: Requirements 2.4**

### Property 7: Export Content Consistency

*For any* repository with stored documentation, exporting as markdown SHALL return content identical to the stored markdown content.

**Validates: Requirements 3.1**

### Property 8: Markdown to HTML Preservation

*For any* valid markdown content, converting to HTML SHALL preserve all structural elements including headings, lists, code blocks, and links.

**Validates: Requirements 9.1**

### Property 9: PDF Validity

*For any* markdown content converted to PDF, the resulting PDF SHALL be a valid PDF file that can be opened by standard PDF readers.

**Validates: Requirements 3.2, 9.2**

### Property 10: PDF Table of Contents

*For any* markdown content with multiple heading levels converted to PDF, the resulting PDF SHALL contain a table of contents with entries corresponding to the markdown headings.

**Validates: Requirements 9.3**

### Property 11: PDF Code Block Preservation

*For any* markdown content containing code blocks, the PDF export SHALL contain those code blocks with preserved content.

**Validates: Requirements 9.5**

### Property 12: Atomic State Transitions

*For any* concurrent requests to update Generation_State for the same repository, the final state SHALL be consistent and reflect exactly one of the requested transitions (no partial updates or race conditions).

**Validates: Requirements 4.6**

### Property 13: Generation Idempotency

*For any* repository, triggering documentation generation multiple times without explicit regeneration SHALL result in only one generation operation executing.

**Validates: Requirements 1.5**

### Property 14: Regeneration Updates

*For any* repository with existing documentation, triggering regeneration SHALL result in new documentation content with an updated creation timestamp that is later than the previous timestamp.

**Validates: Requirements 10.2, 10.3**

### Property 15: Regeneration Atomicity

*For any* repository undergoing regeneration, if the regeneration fails, the previous documentation content SHALL remain unchanged and accessible.

**Validates: Requirements 10.4, 10.5**

### Property 16: Error State Transition

*For any* documentation generation that encounters an error, the Generation_State SHALL transition to 'failed' and an error message SHALL be stored.

**Validates: Requirements 1.4**

### Property 17: Error Logging Completeness

*For any* error that occurs during documentation operations, the system SHALL log detailed error information while returning a user-friendly error message to the client.

**Validates: Requirements 11.5**

### Property 18: Markdown Export Performance

*For any* stored documentation, retrieving and exporting as markdown SHALL complete within 2 seconds.

**Validates: Requirements 3.3, 12.2**

### Property 19: PDF Export Performance

*For any* stored documentation up to 50 pages, converting and exporting as PDF SHALL complete within 10 seconds.

**Validates: Requirements 3.4, 12.3**

### Property 20: Generation Performance

*For any* ArchitectureAnalysis data representing a repository with up to 1000 files, documentation generation SHALL complete within 30 seconds.

**Validates: Requirements 12.1**

### Property 21: Status Endpoint Performance

*For any* repository, querying the documentation status SHALL respond within 500 milliseconds.

**Validates: Requirements 12.5**

### Property 22: PDF Cache Effectiveness

*For any* repository, exporting the same documentation as PDF twice within 1 hour SHALL result in the second export completing faster than the first (cache hit).

**Validates: Requirements 12.4**

## Error Handling

### Error Categories

The system handles four primary error categories:

1. **Validation Errors** (4xx responses)
   - Missing or invalid repository ID
   - Missing architecture analysis data
   - Invalid format parameter
   - Documentation not found

2. **Generation Errors** (500 responses)
   - AI service failures (Bedrock unavailable or rate limited)
   - Invalid analysis data structure
   - Markdown generation failures

3. **Storage Errors** (500 responses)
   - DynamoDB write failures
   - DynamoDB read failures
   - S3 upload failures (for large documents)

4. **Conversion Errors** (500 responses)
   - Markdown to HTML conversion failures
   - HTML to PDF conversion failures
   - Invalid markdown syntax

### Error Handling Strategy

**Validation Errors**:
- Return 400 Bad Request with descriptive error message
- Log warning level with request details
- No retry logic (client must fix request)

**Generation Errors**:
- Update Generation_State to 'failed'
- Store error message in DocumentationRecord
- Return 500 Internal Server Error with user-friendly message
- Log error level with full stack trace
- Support manual retry via regeneration

**Storage Errors**:
- Implement exponential backoff retry (3 attempts)
- If all retries fail, return 500 with storage error message
- Log error level with operation details
- Preserve previous state if update fails

**Conversion Errors**:
- For PDF conversion failures, suggest markdown export as fallback
- Return 500 with conversion error details
- Log error level with markdown content sample
- No automatic retry (likely systematic issue)

### Error Response Format

All error responses follow consistent JSON structure:

```json
{
  "error": {
    "code": "GENERATION_FAILED",
    "message": "Documentation generation failed due to AI service error",
    "details": "The AI service is temporarily unavailable. Please try again in a few minutes.",
    "suggestion": "You can retry generation or contact support if the issue persists."
  }
}
```

### Error Codes

- `MISSING_ANALYSIS`: Architecture analysis not found
- `GENERATION_FAILED`: Documentation generation error
- `STORAGE_FAILED`: Database operation error
- `CONVERSION_FAILED`: Format conversion error
- `NOT_FOUND`: Documentation not found
- `INVALID_FORMAT`: Invalid export format requested
- `INVALID_REQUEST`: Malformed request

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests** focus on:
- Specific error scenarios (missing analysis, AI failures, storage failures)
- API endpoint contracts (status codes, response formats)
- State machine transitions (specific state changes)
- Integration points (AnalysisEngine data consumption, DynamoDB operations)
- Edge cases (empty documentation, very large documents, special characters)

**Property-Based Tests** focus on:
- Universal properties across all inputs (structure, validity, consistency)
- Round-trip properties (store/retrieve, markdown/HTML/PDF conversions)
- Performance properties (timing constraints)
- Concurrency properties (atomic state updates)
- Data fidelity (generated content matches input data)

### Property-Based Testing Configuration

**Framework**: Use `hypothesis` for Python property-based testing

**Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with: `Feature: documentation-generation-export-workflow, Property {number}: {property_text}`
- Custom generators for ArchitectureAnalysis data structures
- Timeout settings for performance properties

**Example Test Structure**:

```python
from hypothesis import given, settings
from hypothesis.strategies import text, integers, lists
import pytest

@settings(max_examples=100)
@given(analysis_data=architecture_analysis_strategy())
def test_property_1_complete_documentation_structure(analysis_data):
    """
    Feature: documentation-generation-export-workflow
    Property 1: For any valid ArchitectureAnalysis data, the generated 
    documentation SHALL contain all required sections.
    """
    generator = DocumentationGenerator(bedrock_client)
    markdown = generator.generate(analysis_data)
    
    required_sections = [
        "## Overview",
        "## Architecture Patterns",
        "## Layers and Components",
        "## Technology Stack",
        "## Data Flows",
        "## Dependencies",
        "## Quality Metrics",
        "## Recommendations"
    ]
    
    for section in required_sections:
        assert section in markdown, f"Missing required section: {section}"
```

### Unit Test Coverage

**DocumentationGenerator Tests**:
- Test with minimal analysis data
- Test with complete analysis data
- Test with missing optional fields
- Test with special characters in content
- Test error handling for invalid data
- Test Mermaid diagram inclusion

**DocumentationStore Tests**:
- Test save and retrieve operations
- Test state transitions
- Test concurrent updates
- Test large document handling (>400KB)
- Test error handling for DynamoDB failures

**ExportService Tests**:
- Test markdown export
- Test PDF conversion pipeline
- Test cache behavior
- Test error handling for conversion failures
- Test large document exports

**API Handler Tests**:
- Test generate endpoint (202 response)
- Test export endpoint (200 with file)
- Test status endpoint (200 with state)
- Test error responses (400, 404, 500)
- Test authentication and authorization

### Integration Tests

**End-to-End Workflow**:
1. Trigger generation → verify 202 response
2. Poll status → verify 'generating' state
3. Wait for completion → verify 'generated' state
4. Export markdown → verify content matches
5. Export PDF → verify valid PDF
6. Trigger regeneration → verify updated content

**Performance Tests**:
- Generate documentation for 1000-file repository (< 30s)
- Export markdown (< 2s)
- Export PDF for 50-page document (< 10s)
- Status query (< 500ms)
- Verify cache effectiveness (second PDF export faster)

### Test Data Generators

**ArchitectureAnalysis Generator**:
```python
from hypothesis.strategies import composite, text, integers, floats, lists

@composite
def architecture_analysis_strategy(draw):
    return ArchitectureAnalysis(
        schema_version="2.0",
        repo_id=draw(text(min_size=1, max_size=50)),
        generated_at=draw(text(regex=r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z')),
        execution_duration_ms=draw(integers(min_value=100, max_value=60000)),
        analysis_level=draw(sampled_from(["basic", "intermediate", "advanced"])),
        statistics=draw(codebase_statistics_strategy()),
        patterns=draw(lists(detected_pattern_strategy(), min_size=0, max_size=5)),
        layers=draw(lists(layer_strategy(), min_size=1, max_size=10)),
        tech_stack=draw(lists(technology_strategy(), min_size=1, max_size=20)),
        # ... other fields
    )
```

### Mocking Strategy

**Bedrock Client Mock**:
- Mock AI responses with realistic markdown content
- Simulate rate limiting and service errors
- Verify correct prompts are sent

**DynamoDB Mock**:
- Use moto library for local DynamoDB simulation
- Test conditional writes and atomic updates
- Simulate throttling and failures

**PDF Conversion Mock**:
- Mock weasyprint for unit tests
- Use real weasyprint for integration tests
- Verify HTML input structure


## Implementation Details

### Technology Stack

**Backend**:
- Python 3.11+ (Lambda runtime)
- boto3 (AWS SDK for DynamoDB, S3)
- markdown library (markdown to HTML conversion)
- weasyprint (HTML to PDF conversion)
- hypothesis (property-based testing)
- pytest (unit testing)

**Frontend**:
- React 18+ with TypeScript
- react-markdown (markdown rendering)
- Tailwind CSS (styling)
- React Query (API state management)

**Infrastructure**:
- AWS Lambda (serverless compute)
- DynamoDB (documentation storage)
- S3 (large document storage, optional)
- API Gateway (REST API)
- CloudWatch (logging and monitoring)

### File Structure

```
backend/
├── handlers/
│   ├── generate_docs.py          # POST /repos/{id}/docs/generate
│   ├── export_docs.py             # GET /repos/{id}/docs/export
│   └── docs_status.py             # GET /repos/{id}/docs/status
├── lib/
│   ├── documentation/
│   │   ├── __init__.py
│   │   ├── generator.py           # DocumentationGenerator class
│   │   ├── store.py               # DocumentationStore class
│   │   ├── exporter.py            # ExportService class
│   │   ├── pdf_converter.py      # PDF conversion utilities
│   │   └── templates.py           # Markdown templates and prompts
│   └── models/
│       └── documentation_models.py # DocumentationRecord dataclass
├── tests/
│   ├── unit/
│   │   ├── test_generator.py
│   │   ├── test_store.py
│   │   └── test_exporter.py
│   ├── property/
│   │   ├── test_properties.py     # Property-based tests
│   │   └── strategies.py          # Hypothesis strategies
│   └── integration/
│       └── test_workflow.py       # End-to-end tests

frontend/
├── src/
│   ├── components/
│   │   ├── docs/
│   │   │   ├── DocumentationPreview.tsx
│   │   │   ├── GenerateButton.tsx
│   │   │   └── ExportDropdown.tsx
│   │   └── architecture/
│   │       └── ArchitectureView.tsx  # Updated with docs controls
│   ├── hooks/
│   │   └── useDocumentation.ts       # Documentation state management
│   └── api/
│       └── documentation.ts          # API client functions
```

### DocumentationGenerator Implementation

**Prompt Engineering**:

The generator uses a structured prompt that includes:
1. System context: "You are a technical documentation writer..."
2. Input data: JSON-serialized ArchitectureAnalysis
3. Output format: Markdown structure specification
4. Constraints: Use only provided data, include all sections, valid markdown

**Example Prompt Structure**:
```
You are a technical documentation writer creating comprehensive repository documentation.

INPUT DATA:
{json_serialized_analysis}

TASK:
Generate complete technical documentation in markdown format with the following sections:
1. Overview - Summarize the repository purpose and architecture
2. Architecture Patterns - Describe detected patterns with confidence scores
3. Layers and Components - Detail each layer and its components
4. Technology Stack - List all technologies with versions and vulnerabilities
5. Data Flows - Describe data flow scenarios with diagrams
6. Dependencies - Analyze dependency tree and issues
7. Quality Metrics - Present health scores and hotspots
8. Recommendations - List prioritized improvement recommendations

CONSTRAINTS:
- Use ONLY the provided data, do not infer or add external information
- Include Mermaid diagrams from the visualizations field
- Use valid markdown syntax
- Be comprehensive but concise
- Format code blocks with appropriate language tags

OUTPUT:
```

**Generation Process**:
1. Validate input ArchitectureAnalysis structure
2. Serialize analysis data to JSON
3. Construct prompt with data and instructions
4. Call Bedrock Claude API with prompt
5. Parse and validate markdown output
6. Return generated markdown

### DocumentationStore Implementation

**DynamoDB Table Configuration**:
```python
Table: RepoDocumentation
Partition Key: repo_id (String)
Billing Mode: PAY_PER_REQUEST
TTL: None (documents persist until deleted)
Point-in-time Recovery: Enabled
Encryption: AWS managed keys

Attributes:
- repo_id: String (PK)
- content: String (up to 400KB)
- content_s3_key: String (optional, for >400KB docs)
- content_hash: String (SHA256)
- generation_state: String
- created_at: String (ISO 8601)
- updated_at: String (ISO 8601)
- error_message: String (optional)
```

**Large Document Handling**:
- If markdown content > 400KB, store in S3
- Store S3 key in DynamoDB record
- Retrieve from S3 when needed
- Use presigned URLs for direct downloads

**Atomic State Updates**:
```python
# Use conditional writes for atomic state transitions
dynamodb.update_item(
    Key={'repo_id': repo_id},
    UpdateExpression='SET generation_state = :new_state, updated_at = :now',
    ConditionExpression='generation_state = :expected_state',
    ExpressionAttributeValues={
        ':new_state': 'generating',
        ':expected_state': 'not_generated',
        ':now': datetime.utcnow().isoformat()
    }
)
```

### ExportService Implementation

**PDF Conversion Pipeline**:

1. **Markdown to HTML**:
```python
import markdown
from markdown.extensions import tables, fenced_code, toc

html = markdown.markdown(
    markdown_content,
    extensions=['tables', 'fenced_code', 'toc', 'codehilite']
)
```

2. **Apply CSS Styling**:
```python
css = """
@page {
    size: A4;
    margin: 2cm;
}
body {
    font-family: 'Helvetica', 'Arial', sans-serif;
    font-size: 11pt;
    line-height: 1.6;
}
h1 { font-size: 24pt; margin-top: 20pt; }
h2 { font-size: 18pt; margin-top: 15pt; }
h3 { font-size: 14pt; margin-top: 10pt; }
code {
    font-family: 'Courier New', monospace;
    background-color: #f4f4f4;
    padding: 2px 4px;
}
pre {
    background-color: #f4f4f4;
    padding: 10px;
    border-left: 3px solid #ccc;
    overflow-x: auto;
}
table {
    border-collapse: collapse;
    width: 100%;
}
th, td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}
"""

full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>{css}</style>
</head>
<body>
    {html}
</body>
</html>
"""
```

3. **HTML to PDF**:
```python
from weasyprint import HTML, CSS
from io import BytesIO

pdf_buffer = BytesIO()
HTML(string=full_html).write_pdf(
    pdf_buffer,
    stylesheets=[CSS(string=css)]
)
pdf_bytes = pdf_buffer.getvalue()
```

**Caching Strategy**:
```python
from functools import lru_cache
from datetime import datetime, timedelta

# In-memory cache with TTL
pdf_cache = {}

def get_cached_pdf(repo_id: str, content_hash: str) -> Optional[bytes]:
    cache_key = f"{repo_id}:{content_hash}"
    if cache_key in pdf_cache:
        cached_data, timestamp = pdf_cache[cache_key]
        if datetime.utcnow() - timestamp < timedelta(hours=1):
            return cached_data
        else:
            del pdf_cache[cache_key]
    return None

def cache_pdf(repo_id: str, content_hash: str, pdf_bytes: bytes):
    cache_key = f"{repo_id}:{content_hash}"
    pdf_cache[cache_key] = (pdf_bytes, datetime.utcnow())
```

### API Handler Implementation

**Generate Handler** (POST /repos/{id}/docs/generate):
```python
async def lambda_handler(event, context):
    repo_id = event['pathParameters']['id']
    store = DocumentationStore()
    
    # Check current state
    current_state = await store.get_state(repo_id)
    if current_state == 'generating':
        return {
            'statusCode': 409,
            'body': json.dumps({'error': 'Generation already in progress'})
        }
    
    # Update state to generating
    try:
        await store.update_state(repo_id, 'generating')
    except ConditionalCheckFailedException:
        return {
            'statusCode': 409,
            'body': json.dumps({'error': 'State conflict, please retry'})
        }
    
    # Start async generation (invoke another Lambda or use Step Functions)
    # For simplicity, generate synchronously here
    try:
        # Get analysis data
        analysis_data = await get_architecture_analysis(repo_id)
        
        # Generate documentation
        generator = DocumentationGenerator(bedrock_client)
        markdown = await generator.generate(analysis_data)
        
        # Store documentation
        await store.save(repo_id, markdown)
        await store.update_state(repo_id, 'generated')
        
        return {
            'statusCode': 202,
            'body': json.dumps({
                'status': 'generating',
                'message': 'Documentation generation started'
            })
        }
    except Exception as e:
        await store.update_state(repo_id, 'failed', str(e))
        logger.error(f"Generation failed for {repo_id}: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': {
                    'code': 'GENERATION_FAILED',
                    'message': 'Documentation generation failed',
                    'details': 'An error occurred during generation. Please try again.'
                }
            })
        }
```

**Export Handler** (GET /repos/{id}/docs/export):
```python
async def lambda_handler(event, context):
    repo_id = event['pathParameters']['id']
    format_param = event['queryStringParameters'].get('format', 'md')
    
    if format_param not in ['md', 'pdf']:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid format. Use md or pdf.'})
        }
    
    store = DocumentationStore()
    exporter = ExportService(store)
    
    try:
        if format_param == 'md':
            content = await exporter.export_markdown(repo_id)
            content_type = 'text/markdown'
            filename = f'{repo_id}-docs.md'
        else:
            content = await exporter.export_pdf(repo_id)
            content_type = 'application/pdf'
            filename = f'{repo_id}-docs.pdf'
        
        # Return as base64-encoded binary
        import base64
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': content_type,
                'Content-Disposition': f'attachment; filename="{filename}"'
            },
            'body': base64.b64encode(content).decode('utf-8'),
            'isBase64Encoded': True
        }
    except NotFoundError:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Documentation not found',
                    'details': 'Please generate documentation first.'
                }
            })
        }
    except Exception as e:
        logger.error(f"Export failed for {repo_id}: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': {
                    'code': 'EXPORT_FAILED',
                    'message': 'Export failed',
                    'details': str(e)
                }
            })
        }
```

**Status Handler** (GET /repos/{id}/docs/status):
```python
async def lambda_handler(event, context):
    repo_id = event['pathParameters']['id']
    store = DocumentationStore()
    
    try:
        doc_record = await store.get(repo_id)
        
        if doc_record is None:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'state': 'not_generated',
                    'created_at': None
                })
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'state': doc_record['generation_state'],
                'created_at': doc_record.get('created_at'),
                'error_message': doc_record.get('error_message')
            })
        }
    except Exception as e:
        logger.error(f"Status check failed for {repo_id}: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to retrieve status'})
        }
```

### Frontend Implementation

**useDocumentation Hook**:
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentationApi } from '../api/documentation';

export function useDocumentation(repoId: string) {
  const queryClient = useQueryClient();
  
  // Query documentation status
  const { data: status, isLoading } = useQuery({
    queryKey: ['documentation', repoId, 'status'],
    queryFn: () => documentationApi.getStatus(repoId),
    refetchInterval: (data) => {
      // Poll every 2s while generating
      return data?.state === 'generating' ? 2000 : false;
    }
  });
  
  // Generate mutation
  const generateMutation = useMutation({
    mutationFn: () => documentationApi.generate(repoId),
    onSuccess: () => {
      queryClient.invalidateQueries(['documentation', repoId, 'status']);
    }
  });
  
  // Export functions
  const exportMarkdown = () => {
    window.location.href = documentationApi.getExportUrl(repoId, 'md');
  };
  
  const exportPdf = () => {
    window.location.href = documentationApi.getExportUrl(repoId, 'pdf');
  };
  
  return {
    status: status?.state || 'not_generated',
    createdAt: status?.created_at,
    errorMessage: status?.error_message,
    isLoading,
    generate: generateMutation.mutate,
    isGenerating: generateMutation.isPending,
    exportMarkdown,
    exportPdf
  };
}
```

**GenerateButton Component**:
```typescript
interface GenerateButtonProps {
  repoId: string;
  status: string;
}

export function GenerateButton({ repoId, status }: GenerateButtonProps) {
  const { generate, isGenerating } = useDocumentation(repoId);
  
  const buttonText = status === 'generated' || status === 'failed'
    ? 'Regenerate Documentation'
    : 'Generate Documentation';
  
  return (
    <button
      onClick={() => generate()}
      disabled={isGenerating}
      className="btn-primary"
    >
      {isGenerating ? (
        <>
          <Spinner className="mr-2" />
          Generating...
        </>
      ) : (
        buttonText
      )}
    </button>
  );
}
```

**ExportDropdown Component**:
```typescript
interface ExportDropdownProps {
  repoId: string;
}

export function ExportDropdown({ repoId }: ExportDropdownProps) {
  const { exportMarkdown, exportPdf } = useDocumentation(repoId);
  
  return (
    <Dropdown>
      <DropdownTrigger>
        <button className="btn-secondary">
          Export Documentation
          <ChevronDownIcon className="ml-2" />
        </button>
      </DropdownTrigger>
      <DropdownMenu>
        <DropdownItem onClick={exportMarkdown}>
          <FileTextIcon className="mr-2" />
          Export as Markdown
        </DropdownItem>
        <DropdownItem onClick={exportPdf}>
          <FilePdfIcon className="mr-2" />
          Export as PDF
        </DropdownItem>
      </DropdownMenu>
    </Dropdown>
  );
}
```

**ArchitectureView Integration**:
```typescript
export function ArchitectureView({ repoId }: { repoId: string }) {
  const { status, isLoading } = useDocumentation(repoId);
  
  return (
    <div className="architecture-view">
      {/* Existing architecture visualization */}
      
      {/* Documentation controls */}
      <div className="documentation-controls">
        {isLoading ? (
          <Spinner />
        ) : status === 'not_generated' || status === 'failed' ? (
          <GenerateButton repoId={repoId} status={status} />
        ) : status === 'generating' ? (
          <div className="flex items-center">
            <Spinner className="mr-2" />
            <span>Generating documentation...</span>
          </div>
        ) : status === 'generated' ? (
          <div className="flex gap-2">
            <GenerateButton repoId={repoId} status={status} />
            <ExportDropdown repoId={repoId} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
```

## Deployment Considerations

### Infrastructure as Code

**SAM Template Updates** (infrastructure/template.yaml):
```yaml
Resources:
  # DynamoDB Table
  RepoDocumentationTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: RepoDocumentation
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: repo_id
          AttributeType: S
      KeySchema:
        - AttributeName: repo_id
          KeyType: HASH
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      SSESpecification:
        SSEEnabled: true
  
  # Lambda Functions
  GenerateDocsFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: backend/
      Handler: handlers.generate_docs.lambda_handler
      Runtime: python3.11
      Timeout: 60
      MemorySize: 1024
      Environment:
        Variables:
          DOCS_TABLE_NAME: !Ref RepoDocumentationTable
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref RepoDocumentationTable
        - Statement:
            - Effect: Allow
              Action:
                - bedrock:InvokeModel
              Resource: '*'
      Events:
        GenerateApi:
          Type: Api
          Properties:
            Path: /repos/{id}/docs/generate
            Method: POST
  
  ExportDocsFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: backend/
      Handler: handlers.export_docs.lambda_handler
      Runtime: python3.11
      Timeout: 30
      MemorySize: 2048  # More memory for PDF conversion
      Environment:
        Variables:
          DOCS_TABLE_NAME: !Ref RepoDocumentationTable
      Policies:
        - DynamoDBReadPolicy:
            TableName: !Ref RepoDocumentationTable
      Events:
        ExportApi:
          Type: Api
          Properties:
            Path: /repos/{id}/docs/export
            Method: GET
  
  DocsStatusFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: backend/
      Handler: handlers.docs_status.lambda_handler
      Runtime: python3.11
      Timeout: 10
      MemorySize: 256
      Environment:
        Variables:
          DOCS_TABLE_NAME: !Ref RepoDocumentationTable
      Policies:
        - DynamoDBReadPolicy:
            TableName: !Ref RepoDocumentationTable
      Events:
        StatusApi:
          Type: Api
          Properties:
            Path: /repos/{id}/docs/status
            Method: GET
```

### Dependencies

**Python Requirements** (backend/requirements.txt):
```
boto3>=1.28.0
markdown>=3.5.0
weasyprint>=60.0
hypothesis>=6.90.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
moto>=4.2.0  # For DynamoDB mocking
```

**Weasyprint System Dependencies**:
Weasyprint requires system libraries. For Lambda, use a Lambda Layer:
```bash
# Create layer with weasyprint and dependencies
docker run --rm -v $(pwd):/var/task lambci/lambda:build-python3.11 \
  pip install weasyprint -t python/lib/python3.11/site-packages/
zip -r weasyprint-layer.zip python
```

### Monitoring and Observability

**CloudWatch Metrics**:
- Documentation generation duration
- Export request count by format
- Error rate by error type
- Cache hit rate for PDF exports
- DynamoDB read/write capacity

**CloudWatch Alarms**:
- High error rate (>5% of requests)
- Long generation duration (>45s)
- DynamoDB throttling
- Lambda timeout errors

**Logging Strategy**:
- Log all generation requests with repo_id
- Log generation duration and token usage
- Log all errors with full context
- Log cache hits/misses
- Use structured logging (JSON format)

### Security Considerations

**Authentication**:
- All endpoints require authentication
- Use API Gateway authorizer (JWT or IAM)
- Validate repo_id ownership

**Authorization**:
- Users can only generate/export docs for their own repositories
- Implement repo ownership checks in handlers

**Data Protection**:
- Encrypt DynamoDB table at rest (AWS managed keys)
- Use HTTPS for all API calls
- Sanitize error messages (no sensitive data)
- Implement rate limiting to prevent abuse

**Input Validation**:
- Validate repo_id format
- Validate format parameter (md or pdf only)
- Validate ArchitectureAnalysis structure
- Sanitize markdown content before PDF conversion

### Performance Optimization

**Lambda Configuration**:
- GenerateDocsFunction: 1024MB memory, 60s timeout
- ExportDocsFunction: 2048MB memory (for PDF), 30s timeout
- DocsStatusFunction: 256MB memory, 10s timeout

**DynamoDB Optimization**:
- Use PAY_PER_REQUEST billing (variable workload)
- Enable point-in-time recovery
- Consider DAX for high read throughput (if needed)

**Caching Strategy**:
- Cache PDFs in Lambda memory (1 hour TTL)
- Consider CloudFront for export downloads
- Cache architecture analysis data to avoid re-fetching

**Async Processing**:
- For very large repositories, use Step Functions for generation
- Send SNS notification when generation completes
- Implement webhook support for completion notifications

### Rollback Strategy

**Deployment Phases**:
1. Deploy DynamoDB table (no impact)
2. Deploy Lambda functions (new endpoints)
3. Deploy frontend changes (feature flag controlled)
4. Enable feature for beta users
5. Monitor metrics and errors
6. Gradual rollout to all users

**Rollback Plan**:
- Feature flag to disable documentation controls in UI
- Keep old generate_docs handler as fallback
- DynamoDB table can remain (no breaking changes)
- Monitor CloudWatch alarms for issues

### Migration Considerations

**Existing Documentation**:
- No existing documentation to migrate (new feature)
- Old generate_docs handler can be deprecated after rollout

**Data Migration**:
- Not applicable (new table)

**API Versioning**:
- Use /v2/repos/{id}/docs/* for new endpoints
- Keep /v1/repos/{id}/docs/* for backward compatibility (if needed)

