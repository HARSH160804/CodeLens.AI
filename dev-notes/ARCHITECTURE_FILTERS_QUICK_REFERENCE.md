# Architecture Endpoint - Quick Reference

## Endpoint

```
GET /repos/{id}/architecture
```

## Query Parameters

### `level` - Analysis Depth
Controls the depth of analysis performed.

**Values**:
- `basic` - High-level overview (fastest)
- `intermediate` - Balanced analysis (default)
- `advanced` - In-depth analysis (slowest)

**Example**:
```
GET /repos/abc123/architecture?level=advanced
```

### `view` - Response Filter
Filters which sections are returned in the response.

**Values**:
- `all` - Complete response (default)
- `summary` - Statistics and basic metadata
- `visualizations` - Diagrams and visual data
- `patterns` - Detected architecture patterns
- `layers` - Layer analysis
- `metrics` - Quality metrics
- `recommendations` - Improvement suggestions
- `tech_stack` - Technology stack with categories
- `dependencies` - Dependency analysis
- `data_flows` - Data flow scenarios

**Example**:
```
GET /repos/abc123/architecture?view=tech_stack
```

### `format` - Visualization Format
Filters which visualization formats are included.

**Values**:
- `all` - All formats (default)
- `mermaid` - Mermaid diagrams only
- `interactive` - Interactive JSON only
- `d3` - D3.js format only
- `cytoscape` - Cytoscape.js format only

**Example**:
```
GET /repos/abc123/architecture?format=mermaid
```

## Response Structure

### Full Response (`view=all`)

```json
{
  "repo_id": "abc123",
  "schema_version": "2.0",
  "generated_at": "2024-03-04T10:30:00Z",
  "execution_duration_ms": 1234,
  "analysis_level": "intermediate",
  
  "statistics": {
    "total_files": 150,
    "total_lines": 12500,
    "primary_language": "Python",
    "language_breakdown": {
      ".py": 80,
      ".js": 40,
      ".json": 30
    },
    "folder_depth": 5,
    "largest_file": {
      "path": "src/main.py",
      "lines": 500
    }
  },
  
  "patterns": [
    {
      "name": "Layered Architecture",
      "confidence": 0.85,
      "evidence_files": ["src/api/", "src/services/", "src/models/"],
      "description": "Clear separation of concerns...",
      "pros": ["Maintainable", "Testable"],
      "cons": ["Can be over-engineered"],
      "alternatives": ["Microservices", "Hexagonal"]
    }
  ],
  
  "layers": [
    {
      "name": "API Layer",
      "description": "REST API endpoints",
      "components": [
        {
          "name": "UserController",
          "type": "controller",
          "file_path": "src/api/users.py",
          "line_count": 150,
          "complexity_score": 3.2,
          "dependencies": ["UserService"],
          "health_score": 0.85,
          "responsibilities": ["Handle HTTP requests", "Validate input"]
        }
      ],
      "technologies": ["Flask", "Pydantic"],
      "entry_points": ["src/api/users.py"],
      "connections": [
        {
          "from_layer": "API Layer",
          "to_layer": "Service Layer",
          "connection_type": "function_call",
          "file_paths": ["src/api/users.py"]
        }
      ]
    }
  ],
  
  "tech_stack": [
    {
      "name": "flask",
      "category": "backend",
      "icon": "si:flask:#000000",
      "version": "2.0.1",
      "latest_version": null,
      "is_deprecated": false,
      "deprecation_warning": null,
      "license": null,
      "vulnerabilities": []
    },
    {
      "name": "react",
      "category": "frontend",
      "icon": "si:react:#61DAFB",
      "version": "18.0.0",
      "latest_version": null,
      "is_deprecated": false,
      "deprecation_warning": null,
      "license": null,
      "vulnerabilities": []
    }
  ],
  
  "data_flows": [
    {
      "name": "User Authentication Flow",
      "description": "User login process",
      "steps": [
        {
          "step_number": 1,
          "component": "API Gateway",
          "action": "Receive login request",
          "next_steps": [2],
          "is_conditional": false
        },
        {
          "step_number": 2,
          "component": "Auth Service",
          "action": "Validate credentials",
          "next_steps": [3, 4],
          "is_conditional": true
        }
      ],
      "bottlenecks": [
        {
          "location": "Database query",
          "severity": "medium",
          "description": "N+1 query pattern",
          "suggested_optimization": "Use eager loading"
        }
      ]
    }
  ],
  
  "dependencies": {
    "dependency_tree": {
      "root": {
        "package_name": "my-app",
        "version": "1.0.0",
        "license": "MIT",
        "depth": 0,
        "children": [],
        "security_status": "safe"
      },
      "total_dependencies": 45,
      "max_depth": 3
    },
    "circular_dependencies": [],
    "outdated_packages": []
  },
  
  "metrics": {
    "health_score": 0.82,
    "complexity_metrics": {
      "average_cyclomatic": 3.5,
      "average_cognitive": 4.2,
      "max_cyclomatic": 15,
      "max_cognitive": 20,
      "high_complexity_files": ["src/utils/parser.py"]
    },
    "hotspots": [
      {
        "file_path": "src/utils/parser.py",
        "type": "complexity",
        "complexity_score": 15,
        "change_frequency": 0.8,
        "severity": "high",
        "recommendation": "Refactor into smaller functions"
      }
    ],
    "technical_debt": {
      "code_duplication_percentage": 5.2,
      "duplicated_blocks": [],
      "test_coverage_gaps": ["src/utils/"],
      "estimated_debt_hours": 12
    }
  },
  
  "recommendations": [
    {
      "id": "rec-001",
      "category": "architecture",
      "title": "Reduce coupling between layers",
      "description": "API layer directly accesses database...",
      "priority": "high",
      "estimated_effort": "4 hours",
      "expected_impact": "Improved maintainability",
      "file_paths": ["src/api/users.py"],
      "code_locations": [
        {
          "file_path": "src/api/users.py",
          "line_start": 45,
          "line_end": 52,
          "snippet": "def get_user():\n    return db.query(User)..."
        }
      ],
      "rationale": "Direct database access violates layered architecture"
    }
  ],
  
  "visualizations": {
    "system_architecture": {
      "diagram_type": "system_architecture",
      "mermaid": "flowchart TD\n    A[Client] --> B[API]\n    B --> C[Service]\n    C --> D[(Database)]",
      "d3_json": {
        "nodes": [
          {
            "id": "client",
            "label": "Client",
            "type": "external",
            "x": 100,
            "y": 100
          }
        ],
        "links": [
          {
            "source": "client",
            "target": "api",
            "label": "HTTP",
            "type": "request"
          }
        ]
      },
      "cytoscape_json": {
        "elements": {
          "nodes": [
            {"data": {"id": "client", "label": "Client"}}
          ],
          "edges": [
            {"data": {"source": "client", "target": "api"}}
          ]
        },
        "layout": {"name": "layered"}
      },
      "metadata": {
        "node_count": 10,
        "edge_count": 15,
        "layout_hints": {
          "viewport": {"width": 800, "height": 600}
        },
        "interaction_handlers": {
          "node_click": "show_component_details",
          "edge_click": "show_connection_details",
          "zoom": "enabled",
          "pan": "enabled"
        }
      }
    },
    "data_flow_scenarios": [
      {
        "name": "Authentication Flow",
        "description": "User login process",
        "mermaid": "sequenceDiagram\n    Client->>API: POST /login",
        "interactive": {
          "nodes": [],
          "edges": []
        }
      }
    ],
    "tech_stack_cards": [
      {
        "name": "React",
        "category": "frontend",
        "icon": "si:react:#61DAFB",
        "version": "18.0.0",
        "description": "JavaScript library for building user interfaces",
        "security_status": "safe",
        "license": "MIT"
      }
    ]
  },
  
  "architecture": {
    "overview": "Layered architecture with clear separation...",
    "architectureStyle": "Layered Architecture",
    "components": [
      {
        "name": "UserController",
        "type": "controller",
        "file_path": "src/api/users.py",
        "role": "API Layer"
      }
    ],
    "dataFlowSteps": [
      "Client sends request",
      "API layer processes request",
      "Business logic executes",
      "Data layer queries database",
      "Response returned to client"
    ],
    "mermaidDiagram": "flowchart TD\n    A[Client] --> B[API]",
    "confidence": 0.85
  },
  
  "diagram": "flowchart TD\n    A[Client] --> B[API]\n    B --> C[Service]\n    C --> D[(Database)]"
}
```

## Technology Categories

Technologies are now intelligently classified into these categories:

- `frontend` - React, Vue, Angular, Svelte
- `backend` - Flask, Django, FastAPI, Express
- `database` - PostgreSQL, MongoDB, MySQL, SQLAlchemy
- `cache` - Redis, Memcached
- `auth` - Passport, OAuth, JWT
- `cloud` - AWS SDK, Azure SDK, GCP SDK
- `testing` - Pytest, Jest, Mocha
- `ml` - TensorFlow, PyTorch, scikit-learn
- `infra` - Docker, Kubernetes, Terraform
- `other` - Unclassified packages

## Icon Format

All technology icons use Simple Icons format:

```
si:slug:color
```

**Examples**:
- `si:flask:#000000` - Flask (black)
- `si:react:#61DAFB` - React (cyan)
- `si:postgresql:#4169E1` - PostgreSQL (blue)
- `si:amazonaws:#FF9900` - AWS (orange)

**Frontend Usage**:
```javascript
// Extract slug from icon string
const icon = "si:flask:#000000";
const [prefix, slug, color] = icon.split(':');

// Use with Simple Icons CDN
const iconUrl = `https://cdn.simpleicons.org/${slug}`;

// Or use the color
const iconColor = color; // "#000000"
```

## Example Queries

### Get only tech stack with icons
```
GET /repos/abc123/architecture?view=tech_stack
```

### Get visualizations in Mermaid format only
```
GET /repos/abc123/architecture?view=visualizations&format=mermaid
```

### Get recommendations for advanced analysis
```
GET /repos/abc123/architecture?level=advanced&view=recommendations
```

### Get metrics and patterns
```
GET /repos/abc123/architecture?view=metrics,patterns
```

## Caching

- Results are cached for 24 hours
- Cache key: `{repo_id}#{level}`
- Subsequent requests return cached results instantly
- Technology classifications cached for 7 days in Redis (if available)

## Performance

### First Request (no cache)
- Basic: ~5-10 seconds
- Intermediate: ~10-20 seconds
- Advanced: ~20-40 seconds

### Subsequent Requests (cached)
- All levels: ~100-200ms

### Technology Classification
- First classification: ~100-500ms per package (PyPI query)
- Cached classification: ~1-2ms per package (Redis)
- Fallback classification: ~1ms per package (static mapping)

## Error Handling

### Partial Failures
If a module fails, the response includes:
```json
{
  "errors": {
    "module_name": "error message"
  },
  "warnings": [
    "module_name analysis unavailable"
  ]
}
```

### Complete Failure
```json
{
  "statusCode": 500,
  "error": "Internal server error: ...",
  "status_code": 500
}
```

## Frontend Integration

### React Example
```typescript
interface ArchitectureResponse {
  repo_id: string;
  schema_version: string;
  generated_at: string;
  execution_duration_ms: number;
  analysis_level: string;
  statistics: Statistics;
  patterns: Pattern[];
  layers: Layer[];
  tech_stack: Technology[];
  data_flows: DataFlow[];
  dependencies: Dependencies;
  metrics: Metrics;
  recommendations: Recommendation[];
  visualizations: Visualizations;
  architecture: LegacyArchitecture;
  diagram: string;
}

// Fetch architecture
const response = await fetch(
  `${API_URL}/repos/${repoId}/architecture?level=intermediate&view=all`
);
const data: ArchitectureResponse = await response.json();

// Render tech stack with icons
data.tech_stack.map(tech => {
  const [prefix, slug, color] = tech.icon.split(':');
  return (
    <div>
      <img src={`https://cdn.simpleicons.org/${slug}`} />
      <span style={{ color }}>{tech.name}</span>
      <span>{tech.category}</span>
    </div>
  );
});
```

## Notes

- Schema version `2.0` includes all new features
- Schema version `1.0` is legacy format (backward compatible)
- All timestamps are in ISO 8601 format with UTC timezone
- Confidence scores are 0.0-1.0 (0% to 100%)
- Health scores are 0.0-1.0 (0% to 100%)
- Complexity scores are unbounded (higher = more complex)
