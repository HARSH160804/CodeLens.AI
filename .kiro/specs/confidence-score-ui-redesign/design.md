# Design Document: Confidence Score UI Redesign

## Overview

This design document specifies the technical approach for redesigning the Architecture Confidence Score visualization from a vertical layout to a horizontal, compact layout. The redesign aims to improve information density and visual hierarchy while maintaining all existing functionality and data integrity.

### Current State

The existing confidence score component in `ArchitectureView_Enhanced.tsx` uses a vertical layout:
- Large confidence score displayed at the top (centered)
- Quality label below the score
- Individual metrics stacked vertically below with progress bars
- Each metric takes a full row with name, percentage, description, and progress bar

### Target State

The redesigned component will use a horizontal layout:
- Title "Architecture Confidence" on the left
- Confidence score and quality label in the center-left area
- All metrics displayed horizontally on the right side
- Compact, single-row layout (with responsive wrapping on narrow screens)

### Design Goals

1. **Improved Information Density**: Display all confidence information in a more compact horizontal layout
2. **Better Visual Hierarchy**: Clear left-to-right reading flow from title → score → metrics
3. **Maintained Functionality**: Preserve all existing data, calculations, and color coding
4. **Seamless Integration**: Minimal changes to parent component (ArchitectureView)
5. **Responsive Design**: Graceful degradation on smaller screens

## Architecture

### Component Structure

The redesign will refactor the existing inline confidence score rendering into a more maintainable structure while keeping it within the same file:

```
ArchitectureView_Enhanced.tsx
├── ArchitectureView (main component)
│   ├── Helper functions (existing)
│   │   ├── getConfidence()
│   │   ├── getConfidenceSignals()
│   │   ├── getConfidenceColor()
│   │   └── getConfidenceLabel()
│   └── Confidence Score Section (refactored inline JSX)
│       ├── Title Section (left)
│       ├── Score Display Section (center-left)
│       └── Metrics Section (right, horizontal)
```

### Layout Strategy

The horizontal layout will be implemented using CSS Flexbox:

```
┌─────────────────────────────────────────────────────────────────┐
│ [Title]  [Score + Label]  [Metric 1] [Metric 2] [Metric 3] ... │
└─────────────────────────────────────────────────────────────────┘
```

**Flexbox Configuration**:
- Container: `flex flex-row items-center gap-6`
- Title section: Fixed width, left-aligned
- Score section: Fixed width, center-left
- Metrics section: `flex-1`, horizontal flex container with wrapping

### Responsive Behavior

**Breakpoint Strategy**:
- **Desktop (≥1024px)**: Full horizontal layout, all elements in one row
- **Tablet (768px-1023px)**: Horizontal layout with metrics wrapping to second row if needed
- **Mobile (<768px)**: Vertical stacking (fallback to current behavior)

## Components and Interfaces

### Data Structures

The component will continue to use the existing data structures from the API response:

```typescript
interface ArchitectureResponse {
  confidence: number  // 0.0 to 1.0
  confidence_signals: {
    layer_separation_score: number
    dependency_direction_score: number
    dependency_depth_score: number
    naming_consistency_score: number
    framework_detection_score: number
    database_integration_score: number
  }
  // ... other fields
}
```

### Helper Functions (Existing)

These functions will be reused without modification:

```typescript
// Get confidence value with fallback
const getConfidence = (): number => {
  if (currentArchitecture?.confidence !== undefined) {
    return currentArchitecture.confidence
  }
  if (currentArchitecture?.architecture?.confidence !== undefined) {
    return currentArchitecture.architecture.confidence
  }
  return 0.5 // Default fallback
}

// Get confidence signals with fallback
const getConfidenceSignals = () => {
  const signals = currentArchitecture?.confidence_signals
  if (!signals || typeof signals !== 'object') {
    return {
      layer_separation_score: 0,
      framework_detection_score: 0,
      database_integration_score: 0,
      dependency_direction_score: 0,
      dependency_depth_score: 0,
      naming_consistency_score: 0,
    }
  }
  return signals
}

// Get color class based on confidence value
const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.85) return 'text-green-400'
  if (confidence >= 0.70) return 'text-blue-400'
  if (confidence >= 0.50) return 'text-yellow-400'
  return 'text-red-400'
}

// Get quality label based on confidence value
const getConfidenceLabel = (confidence: number): string => {
  if (confidence >= 0.85) return 'Excellent'
  if (confidence >= 0.70) return 'Good'
  if (confidence >= 0.50) return 'Fair'
  return 'Poor'
}
```

### Metric Configuration

The metrics will be defined with their display properties:

```typescript
const metrics = [
  {
    key: 'layer_separation_score',
    label: 'Layer Separation',
    color: 'structural'
  },
  {
    key: 'dependency_direction_score',
    label: 'Dependency Direction',
    color: 'structural'
  },
  {
    key: 'dependency_depth_score',
    label: 'Dependency Depth',
    color: 'structural'
  },
  {
    key: 'naming_consistency_score',
    label: 'Naming Consistency',
    color: 'quality'
  },
  {
    key: 'framework_detection_score',
    label: 'Framework Detection',
    color: 'structural'
  },
  {
    key: 'database_integration_score',
    label: 'Database Integration',
    color: 'structural'
  }
]
```

## Data Models

### Color Coding Logic

**Confidence Score Colors** (0-100%):
- 0-40%: Red (`text-red-400`)
- 41-70%: Yellow (`text-yellow-400`)
- 71-100%: Green (`text-green-400`)

Note: The existing implementation uses different thresholds (50%, 70%, 85%) with blue for mid-high range. The design will preserve the existing logic:
- 0-49%: Red (`text-red-400`)
- 50-69%: Yellow (`text-yellow-400`)
- 70-84%: Blue (`text-blue-400`)
- 85-100%: Green (`text-green-400`)

**Progress Bar Colors**:
- Structural metrics (layer separation, dependency direction, etc.):
  - ≥70%: Green (`#10b981`)
  - 50-69%: Blue (`#3b82f6`)
  - <50%: Yellow (`#fbbf24`)
- Quality metrics (naming consistency):
  - ≥70%: Green (`#10b981`)
  - 50-69%: Orange (`#f59e0b`)
  - <50%: Red (`#ef4444`)

### Theme Colors

The component will use the existing color palette:

**Background Colors**:
- Primary background: `#0a0e14`
- Secondary background: `#151b24`
- Tertiary background: `#0d1117`
- Progress bar background: `#0a0d12`

**Text Colors**:
- Primary text: `text-white`
- Secondary text: `text-gray-300`
- Tertiary text: `text-gray-400`
- Quaternary text: `text-gray-500`

**Border Colors**:
- Primary border: `#151b24`
- Subtle border: `rgba(255, 255, 255, 0.1)`

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing the prework, I've identified the following redundancies and consolidations:

**Redundancies to eliminate**:
- Properties 2.5, 2.6, 2.7 (specific color ranges) are edge cases of Property 2.3 (general color coding)
- Property 2.4 (quality label color matches score color) is a consistency check that can be combined with 2.3
- Properties 3.3 and 3.4 (positioning of metric elements) can be combined into a single layout property
- Properties 4.2, 4.3, 4.4, 4.5 (specific style values) are all examples of Property 4.1 (theme consistency)

**Properties to combine**:
- Combine 1.1, 1.4, 1.5 into a single comprehensive horizontal layout property
- Combine 3.2, 3.3, 3.4 into a single metric display structure property
- Combine 6.3, 6.4, 6.5 into a single backward compatibility property

This reduces the property count from 30+ potential properties to approximately 15 unique, non-redundant properties.

### Property 1: Horizontal Layout Structure

*For any* confidence score data, when the component renders at desktop viewport width (≥1024px), all major sections (title, score, metrics) should be arranged in a single horizontal row using flexbox layout.

**Validates: Requirements 1.1, 1.4, 1.5**

### Property 2: Non-Zero Metric Filtering

*For any* set of confidence signals, only metrics with non-zero values should be displayed in the metrics section, and metrics with zero values should be completely hidden from the rendered output.

**Validates: Requirements 3.1, 3.6**

### Property 3: Metric Display Structure

*For any* non-zero metric, the rendered output should contain the metric name, percentage value, and progress bar, with the name and percentage displayed above the progress bar.

**Validates: Requirements 3.2, 3.3, 3.4**

### Property 4: Confidence Score Color Coding

*For any* confidence score value, the color applied to both the confidence score and quality label should match the value range: red for <50%, yellow for 50-69%, blue for 70-84%, and green for ≥85%.

**Validates: Requirements 2.3, 2.4**

### Property 5: Progress Bar Color Coding

*For any* metric value, the progress bar color should be determined by the metric type (structural vs quality) and value range, with structural metrics using green/blue/yellow and quality metrics using green/orange/red.

**Validates: Requirements 3.5**

### Property 6: Percentage Display Format

*For any* confidence score or metric value (0.0 to 1.0), the displayed percentage should be the value multiplied by 100 and formatted with no decimal places (e.g., 0.75 → "75%").

**Validates: Requirements 2.1**

### Property 7: Responsive Wrapping Behavior

*For any* viewport width, when the horizontal space is insufficient to display all metrics in a single row, the metrics section should wrap to multiple rows while maintaining the horizontal arrangement within each row.

**Validates: Requirements 5.1, 5.2**

### Property 8: Backward Compatibility - Helper Functions

*For any* confidence score data, the component should produce the same confidence value, quality label, color class, and metric values as the current implementation when using the same helper functions.

**Validates: Requirements 6.1, 6.3, 6.5**

### Property 9: Backward Compatibility - Data Source

*For any* architecture response, the component should retrieve confidence and metric data from the same fields (confidence, confidence_signals) as the current implementation.

**Validates: Requirements 6.2, 6.4**

### Property 10: Theme Color Consistency

*For any* rendered element in the confidence score component, the background colors, text colors, and border colors should match the existing application theme palette.

**Validates: Requirements 4.1**

## Error Handling

### Missing Data Handling

The component will gracefully handle missing or invalid data:

1. **Missing Confidence Value**: Fall back to 0.5 (50%) using existing `getConfidence()` logic
2. **Missing Confidence Signals**: Fall back to all zeros using existing `getConfidenceSignals()` logic
3. **Invalid Metric Values**: Treat as zero and hide from display
4. **Null/Undefined Architecture**: Component should not render (handled by parent)

### Edge Cases

1. **All Metrics Zero**: Display only title and confidence score, hide metrics section entirely
2. **Very Long Metric Names**: Truncate with ellipsis if needed (unlikely with current metric names)
3. **Extreme Viewport Widths**: 
   - Very wide: Metrics may have excessive spacing (acceptable)
   - Very narrow: Fall back to vertical layout

### Error States

The component itself does not handle error states (loading, API errors) as these are managed by the parent `ArchitectureView` component.

## Testing Strategy

### Dual Testing Approach

The feature will be tested using both unit tests and property-based tests:

**Unit Tests**: Focus on specific examples, edge cases, and integration points
- Specific confidence score values (0%, 50%, 75%, 100%)
- Specific metric configurations (all zero, mixed values, all non-zero)
- Specific viewport widths (mobile, tablet, desktop)
- Theme color values
- Helper function outputs

**Property Tests**: Focus on universal properties across all inputs
- Color coding logic for all possible confidence values
- Metric filtering for all possible signal combinations
- Layout structure for all viewport widths
- Percentage formatting for all numeric values
- Backward compatibility for all valid architecture responses

### Property-Based Testing Configuration

**Testing Library**: `@fast-check/jest` (for TypeScript/React)

**Test Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with feature name and property number
- Tag format: `Feature: confidence-score-ui-redesign, Property {number}: {property_text}`

**Example Property Test Structure**:

```typescript
import fc from 'fast-check'

describe('Feature: confidence-score-ui-redesign', () => {
  it('Property 4: Confidence Score Color Coding', () => {
    fc.assert(
      fc.property(
        fc.float({ min: 0, max: 1 }), // Generate random confidence values
        (confidence) => {
          const color = getConfidenceColor(confidence)
          
          if (confidence < 0.5) {
            expect(color).toBe('text-red-400')
          } else if (confidence < 0.7) {
            expect(color).toBe('text-yellow-400')
          } else if (confidence < 0.85) {
            expect(color).toBe('text-blue-400')
          } else {
            expect(color).toBe('text-green-400')
          }
        }
      ),
      { numRuns: 100 }
    )
  })
})
```

### Unit Testing Focus Areas

1. **Specific Examples**:
   - Render with confidence score of 0.85 (excellent)
   - Render with confidence score of 0.45 (poor)
   - Render with all metrics at 0.75
   - Render with mixed metric values

2. **Edge Cases**:
   - All metrics are zero
   - Only one metric is non-zero
   - Confidence score at exact threshold values (0.5, 0.7, 0.85)
   - Missing confidence_signals object

3. **Integration Points**:
   - Component renders within ArchitectureView
   - Helper functions are called correctly
   - Theme colors are applied correctly
   - Responsive classes are applied at breakpoints

### Test Coverage Goals

- **Line Coverage**: >90%
- **Branch Coverage**: >85%
- **Property Test Coverage**: All 10 correctness properties
- **Unit Test Coverage**: All edge cases and examples from requirements

### Testing Tools

- **Unit Testing**: Jest + React Testing Library
- **Property Testing**: @fast-check/jest
- **Visual Regression**: Chromatic (optional, for UI verification)
- **Accessibility**: jest-axe (ensure WCAG compliance)

