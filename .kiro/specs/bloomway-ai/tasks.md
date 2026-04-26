# Implementation Plan: CodeLens - Frontend AI Components

## Overview

This implementation plan focuses on completing the remaining frontend AI interaction components for CodeLens. The backend Lambda handlers, core libraries, and infrastructure are already complete. The frontend layout and navigation components are also complete. This plan covers the implementation of the four remaining AI interaction components and their integration with the backend APIs.

## Tasks

- [x] 1. Update API service layer with complete endpoint signatures
  - [x] 1.1 Update API service to match backend endpoint structure
    - Update `ingestRepository` to accept source_type and auth_token
    - Update `getArchitecture` to accept level parameter
    - Update `explainFile` to accept level parameter and use correct endpoint path
    - Update `chat` to accept full request body (scope, history)
    - Update `exportDocumentation` to accept format parameter
    - Add TypeScript interfaces for all request/response types
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 1.2 Write unit tests for API service
    - Test request construction for all endpoints
    - Test response parsing and error handling
    - Use MSW to mock API responses
    - _Requirements: 8.6, 8.7_

- [x] 2. Implement ExplanationPanel component
  - [x] 2.1 Create ExplanationPanel component with tab interface
    - Create component in `frontend/src/components/code/ExplanationPanel.tsx`
    - Implement tab switcher for beginner/intermediate/advanced levels
    - Display explanation sections: purpose, key functions, patterns, dependencies
    - Show complexity metrics (LOC, function count)
    - Display related files with navigation links
    - Add loading and error states
    - _Requirements: 7.5, 3.1, 3.2, 3.3, 3.4_

  - [ ]* 2.2 Write unit tests for ExplanationPanel
    - Test tab switching behavior
    - Test rendering of explanation sections
    - Test loading and error states
    - Test related file link clicks
    - _Requirements: 7.5_

- [x] 3. Implement ArchitectureView component
  - [x] 3.1 Create ArchitectureView component with diagram rendering
    - Create component in `frontend/src/components/architecture/ArchitectureView.tsx`
    - Render architecture overview text
    - Display component list with descriptions
    - Show pattern badges
    - Render Mermaid diagram using mermaid.js
    - Add level selector (basic/intermediate/advanced)
    - Display entry points with file links
    - Add loading and error states
    - _Requirements: 7.3, 2.1, 2.2, 2.3, 2.5, 2.6_

  - [ ]* 3.2 Write unit tests for ArchitectureView
    - Test component rendering
    - Test level selector functionality
    - Test Mermaid diagram rendering
    - Test loading and error states
    - _Requirements: 7.3_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement ChatInterface component
  - [x] 5.1 Create ChatInterface component with message list
    - Create component in `frontend/src/components/chat/ChatInterface.tsx`
    - Display message list with user/assistant bubbles
    - Implement input field with send button
    - Show citations with file links in format [file:line]
    - Display suggested questions as clickable chips
    - Add confidence indicator (high/medium/low)
    - Implement scope selector (all/file/directory)
    - Manage conversation history state
    - Add loading state during message generation
    - Handle empty vector store errors gracefully
    - _Requirements: 7.6, 7.7, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 10.4_

  - [ ]* 5.2 Write unit tests for ChatInterface
    - Test message rendering
    - Test input submission
    - Test citation link clicks
    - Test suggested question clicks
    - Test scope selector
    - Test conversation history management
    - Test loading and error states
    - _Requirements: 7.6, 7.7_

- [x] 6. Implement DocGenerator component
  - [x] 6.1 Create DocGenerator component with export functionality
    - Create component in `frontend/src/components/docs/DocGenerator.tsx`
    - Add format selector (Markdown/PDF)
    - Implement export button with loading state
    - Display download link when export completes
    - Show preview of documentation structure
    - Handle export errors gracefully
    - _Requirements: 7.8, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ]* 6.2 Write unit tests for DocGenerator
    - Test format selector
    - Test export button click
    - Test download link display
    - Test loading and error states
    - _Requirements: 7.8_

- [x] 7. Integrate components into existing pages
  - [x] 7.1 Integrate ExplanationPanel into FileViewPage
    - Import and render ExplanationPanel in FileViewPage
    - Pass file path and repository ID as props
    - Fetch explanation data on file selection
    - Handle level switching
    - _Requirements: 7.5, 3.1_

  - [x] 7.2 Integrate ArchitectureView into ArchitecturePage
    - Import and render ArchitectureView in ArchitecturePage
    - Pass repository ID as prop
    - Fetch architecture data on page load
    - Handle level switching
    - _Requirements: 7.3, 2.1_

  - [x] 7.3 Add ChatInterface to main layout or dedicated page
    - Create ChatPage or add ChatInterface to MainLayout
    - Pass session ID and repository ID as props
    - Initialize chat session on page load
    - Handle message submission and history
    - _Requirements: 7.6, 7.7, 4.7_

  - [x] 7.4 Add DocGenerator to appropriate location
    - Add DocGenerator to ArchitecturePage or create dedicated export page
    - Pass session ID as prop
    - Handle export completion and download
    - _Requirements: 7.8, 5.4_

- [x] 8. Add error boundaries and loading states
  - [x] 8.1 Create ErrorBoundary component
    - Create component in `frontend/src/components/common/ErrorBoundary.tsx`
    - Catch and display component errors gracefully
    - Provide retry functionality
    - Log errors for debugging
    - _Requirements: 10.1, 10.2, 10.3, 10.5_

  - [x] 8.2 Add global loading states
    - Create LoadingSpinner component
    - Add loading indicators for API calls
    - Implement skeleton screens for content loading
    - _Requirements: 7.2_

  - [ ]* 8.3 Write unit tests for error handling
    - Test ErrorBoundary error catching
    - Test retry functionality
    - Test loading state transitions
    - _Requirements: 10.1, 10.2, 10.3, 10.5_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The backend APIs are already complete and deployed
- Focus on TypeScript type safety and error handling
- Use Tailwind CSS for consistent styling with existing components
- Mermaid.js should be added as a dependency for diagram rendering
- All components should support dark mode (already default theme)
