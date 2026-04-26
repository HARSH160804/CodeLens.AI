# Implementation Plan: Confidence Score UI Redesign

## Overview

This implementation plan refactors the confidence score section in `ArchitectureView_Enhanced.tsx` from a vertical layout to a horizontal, compact layout. The redesign improves information density and visual hierarchy while maintaining all existing functionality, data calculations, and color coding logic.

The implementation will:
- Transform the existing inline confidence score JSX into a horizontal layout
- Maintain all existing helper functions and data structures
- Preserve backward compatibility with the current API response format
- Add property-based tests and unit tests to verify correctness

## Tasks

- [x] 1. Refactor confidence score section to horizontal layout
  - Extract the confidence score rendering logic (currently around lines 400-500) into a more maintainable structure
  - Implement horizontal flexbox layout with three sections: title (left), score display (center-left), metrics (right)
  - Use `flex flex-row items-center gap-6` for the main container
  - Maintain all existing helper functions: `getConfidence()`, `getConfidenceSignals()`, `getConfidenceColor()`, `getConfidenceLabel()`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.1, 7.3, 7.4_

- [ ]* 1.1 Write property test for horizontal layout structure
  - **Property 1: Horizontal Layout Structure**
  - **Validates: Requirements 1.1, 1.4, 1.5**
  - Test that all major sections render in horizontal arrangement at desktop viewport width

- [x] 2. Implement title section
  - Add "Architecture Confidence" title on the left side of the layout
  - Use fixed width for consistent spacing
  - Apply existing text color classes (`text-white`, `text-lg`, `font-bold`)
  - _Requirements: 1.2, 4.3_

- [x] 3. Implement score display section
  - Display confidence score as large percentage value (center-left area)
  - Display quality label directly below the score
  - Apply color coding based on confidence value using existing `getConfidenceColor()` function
  - Use fixed width for the score section to maintain layout stability
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 7.2_

- [ ]* 3.1 Write property test for confidence score color coding
  - **Property 4: Confidence Score Color Coding**
  - **Validates: Requirements 2.3, 2.4**
  - Test color coding logic for all confidence values (0.0 to 1.0)

- [ ]* 3.2 Write property test for percentage display format
  - **Property 6: Percentage Display Format**
  - **Validates: Requirements 2.1**
  - Test that all values (0.0 to 1.0) are correctly formatted as percentages

- [x] 4. Implement metrics section with horizontal display
  - Display all non-zero metrics in horizontal arrangement on the right side
  - Use `flex-1` to allow metrics section to grow and fill available space
  - Implement metric filtering to hide metrics with zero values
  - For each metric: display name, percentage value, and progress bar
  - Position metric name and percentage above the progress bar
  - Apply color coding to progress bars based on metric type and value
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 6.2, 6.4, 6.5_

- [ ]* 4.1 Write property test for non-zero metric filtering
  - **Property 2: Non-Zero Metric Filtering**
  - **Validates: Requirements 3.1, 3.6**
  - Test that only non-zero metrics are displayed

- [ ]* 4.2 Write property test for metric display structure
  - **Property 3: Metric Display Structure**
  - **Validates: Requirements 3.2, 3.3, 3.4**
  - Test that each metric contains name, percentage, and progress bar

- [ ]* 4.3 Write property test for progress bar color coding
  - **Property 5: Progress Bar Color Coding**
  - **Validates: Requirements 3.5**
  - Test progress bar colors for all metric types and value ranges

- [x] 5. Implement responsive behavior
  - Add responsive wrapping for metrics section using `flex-wrap`
  - Ensure horizontal layout is maintained at desktop viewport (≥1024px)
  - Allow metrics to wrap to new rows on smaller viewports
  - Maintain readable text sizes and proportional spacing at all viewport widths
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ]* 5.1 Write property test for responsive wrapping behavior
  - **Property 7: Responsive Wrapping Behavior**
  - **Validates: Requirements 5.1, 5.2**
  - Test layout behavior at different viewport widths

- [x] 6. Apply visual styling and theme consistency
  - Use existing background colors: `#0a0e14`, `#151b24`, `#0d1117`
  - Use existing text color classes: `text-gray-300`, `text-gray-400`, `text-gray-500`
  - Maintain existing progress bar height (`h-2`)
  - Apply existing border radius and padding styles
  - Ensure progress bar background color matches existing implementation (`#0a0d12`)
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ]* 6.1 Write property test for theme color consistency
  - **Property 10: Theme Color Consistency**
  - **Validates: Requirements 4.1**
  - Test that all rendered elements use the correct theme colors

- [x] 7. Verify backward compatibility
  - Ensure component uses same data source (confidence, confidence_signals fields)
  - Verify helper functions produce same outputs as before refactoring
  - Confirm quality label values match current implementation
  - Test that all metrics from current implementation are displayed when non-zero
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.2_

- [ ]* 7.1 Write property test for backward compatibility - helper functions
  - **Property 8: Backward Compatibility - Helper Functions**
  - **Validates: Requirements 6.1, 6.3, 6.5**
  - Test that helper functions produce same results as current implementation

- [ ]* 7.2 Write property test for backward compatibility - data source
  - **Property 9: Backward Compatibility - Data Source**
  - **Validates: Requirements 6.2, 6.4**
  - Test that component retrieves data from same fields as current implementation

- [ ]* 7.3 Write unit tests for edge cases
  - Test all metrics are zero (should hide metrics section)
  - Test only one metric is non-zero
  - Test confidence score at exact threshold values (0.5, 0.7, 0.85)
  - Test missing confidence_signals object
  - Test missing confidence value (should fall back to 0.5)

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The refactoring maintains all existing functionality while improving the layout
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples and edge cases
- All helper functions (`getConfidence`, `getConfidenceSignals`, `getConfidenceColor`, `getConfidenceLabel`) are reused without modification
- The implementation preserves the existing color coding thresholds (50%, 70%, 85%)
- No changes are required to the parent component or API response format
