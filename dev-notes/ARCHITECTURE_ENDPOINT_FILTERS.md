# Architecture Endpoint - Query Parameter Filters

## Overview

The `/repos/{id}/architecture` endpoint now supports flexible query parameter filtering for demo and development purposes. This allows you to request specific sections of the analysis or specific visualization formats without receiving the full response.

## Endpoint

```
GET /repos/{repo_id}/architecture
```

## Query Parameters

### `level` (string)
Analysis depth level.

**Values**: `basic` | `intermediate` | `advanced`  
**Default**: `intermediate`

- `basic`: High-level overview for beginners
- `intermediate`: Balanced analysis (default)
- `advanced`: In-depth analysis with design patterns and technical debt

### `view` (string)
Filter which sections of the analysis to return.

**Values**: `all` | `summary` | `visualizations` | `patterns` | `layers` | `metrics` | `recommendations` | `tech_stack` | `dependencies` | `data_flows`  
**Default**: `all`

- `all`: Full analysis response (default)
- `summary`: Statistics, execution time, and basic metadata
- `visualizations`: All visualization data and diagrams
- `patterns`: Detected architectural patterns only
- `layers`: Layer analysis only
- `metrics`: Quality metrics and statistics
- `recommendations`: Architecture recommendations only
- `tech_stack`: Technology stack with tech cards
- `dependencies`: Dependency analysis only
- `data_flows`: Data flow scenarios only

### `format` (string)
Filter visualization formats (only applies when visualizations are included).

**Values**: `all` | `mermaid` | `interactive` | `d3` | `cytoscape`  
**Default**: `all`

- `all`: All visualization formats (default)
- `mermaid`: Mermaid diagram syntax only
- `interactive`: Interactive JSON format (D3-compatible)
- `d3`: D3.js-specific JSON format
- `cytoscape`: Cytoscape.js-specific JSON format

## Examples

### 1. Full Response (Default)
```bash
GET /repos/{repo_id}/architecture
```

Returns complete analysis with all sections and all visualization formats.

### 2. Summary Only
```bash
GET /repos/{repo_id}/architecture?view=summary
```

Returns:
```json
{
  "repo_id": "uuid",
  "schema_version": "2.0",
  "generated_at": "2024-01-15T10:30:00Z",
  "analysis_level": "intermediate",
  "statistics": {
    "total_files": 150,
    "total_lines": 12500,
    "primary_language": "Python"
  },
  "execution_duration_ms": 1234,
  "architecture": {
    "overview": "...",
    "architectureStyle": "Layered"
  }
}
```

### 3. Visualizations Only
```bash
GET /repos/{repo_id}/architecture?view=visualizations
```

Returns only the visualizations section with all formats.

### 4. Patterns Only
```bash
GET /repos/{repo_id}/architecture?view=patterns
```

Returns:
```json
{
  "repo_id": "uuid",
  "schema_version": "2.0",
  "generated_at": "2024-01-15T10:30:00Z",
  "analysis_level": "intermediate",
  "patterns": [
    {
      "name": "Layered Architecture",
      "confidence": 0.85,
      "evidence_files": ["src/api/", "src/services/"],
      "description": "...",
      "pros": [...],
      "cons": [...],
      "alternatives": [...]
    }
  ]
}
```

### 5. Mermaid Diagrams Only
```bash
GET /repos/{repo_id}/architecture?view=visualizations&format=mermaid
```

Returns visualizations with only Mermaid syntax (no D3/Cytoscape JSON).

### 6. Interactive Format Only
```bash
GET /repos/{repo_id}/architecture?view=visualizations&format=interactive
```

Returns visualizations with interactive JSON format suitable for D3.js rendering.

### 7. Tech Stack with Cards
```bash
GET /repos/{repo_id}/architecture?view=tech_stack
```

Returns:
```json
{
  "repo_id": "uuid",
  "schema_version": "2.0",
  "generated_at": "2024-01-15T10:30:00Z",
  "analysis_level": "intermediate",
  "tech_stack": [
    {
      "name": "React",
      "category": "frontend",
      "version": "18.2.0",
      "vulnerabilities": []
    }
  ],
  "tech_stack_cards": {
    "categories": {
      "frontend": [...],
      "backend": [...],
      "database": [...]
    },
    "summary": {
      "total": 15,
      "secure": 12,
      "vulnerable": 2,
      "outdated": 1
    },
    "recommendations": [...]
  }
}
```

### 8. Data Flow Scenarios
```bash
GET /repos/{repo_id}/architecture?view=data_flows
```

Returns:
```json
{
  "repo_id": "uuid",
  "schema_version": "2.0",
  "generated_at": "2024-01-15T10:30:00Z",
  "analysis_level": "intermediate",
  "data_flows": [...],
  "data_flow_scenarios": [
    {
      "id": "auth_flow",
      "name": "User Authentication",
      "description": "Complete login/logout flow",
      "mermaid_sequence": "sequenceDiagram...",
      "steps": [...],
      "estimated_latency_ms": 100,
      "critical_path": [...],
      "failure_points": [...]
    }
  ]
}
```

### 9. Advanced Analysis with Recommendations
```bash
GET /repos/{repo_id}/architecture?level=advanced&view=recommendations
```

Returns detailed recommendations from advanced-level analysis.

### 10. Metrics and Statistics
```bash
GET /repos/{repo_id}/architecture?view=metrics
```

Returns:
```json
{
  "repo_id": "uuid",
  "schema_version": "2.0",
  "generated_at": "2024-01-15T10:30:00Z",
  "analysis_level": "intermediate",
  "statistics": {
    "total_files": 150,
    "total_lines": 12500
  },
  "metrics": {
    "health_score": 75.5,
    "complexity_metrics": {
      "average_cyclomatic": 5.2,
      "average_cognitive": 8.1
    },
    "hotspots": [...],
    "technical_debt": {
      "code_duplication_percentage": 3.5,
      "estimated_debt_hours": 24
    }
  }
}
```

## Use Cases

### Demo Purposes
- Show specific analysis sections without overwhelming the audience
- Focus on visualizations for architecture presentations
- Highlight metrics for code quality discussions

### Development
- Reduce payload size for faster testing
- Focus on specific sections during development
- Test individual analysis modules

### Frontend Integration
- Request only needed data for specific UI components
- Reduce bandwidth for mobile/slow connections
- Implement progressive loading (summary first, then details)

### API Exploration
- Understand the structure of each section independently
- Test different visualization formats
- Compare analysis levels (basic vs advanced)

## Response Structure

All filtered responses maintain the base structure:
```json
{
  "repo_id": "string",
  "schema_version": "2.0",
  "generated_at": "ISO 8601 timestamp",
  "analysis_level": "basic|intermediate|advanced",
  // ... filtered sections based on view parameter
}
```

## Caching

- Caching is based on `repo_id` and `level` only
- View and format filters are applied after cache retrieval
- Full analysis is always cached, filters are applied on-demand

## Error Responses

### Invalid View
```json
{
  "error": "Invalid view: invalid_view. Must be one of all, summary, visualizations, patterns, layers, metrics, recommendations, tech_stack, dependencies, data_flows",
  "status_code": 400
}
```

### Invalid Format
```json
{
  "error": "Invalid format: invalid_format. Must be one of all, mermaid, interactive, d3, cytoscape",
  "status_code": 400
}
```

## Architecture Notes

- **Analysis Engine Integration**: Filters are applied AFTER Analysis Engine completes
- **No Performance Impact**: Full analysis runs regardless of filters
- **Backward Compatible**: Default behavior (no query params) returns full response
- **Lightweight**: Filtering is simple JSON manipulation, no additional processing

## Testing

Use the provided test script:
```bash
./test_architecture_filters.sh
```

Update `REPO_ID` variable with your repository ID before running.
