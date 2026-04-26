// Quick test file to verify component structure

// Mock data for testing
const mockLayers = [
  {
    name: 'frontend',
    description: 'Frontend layer',
    components: [
      {
        name: 'App',
        type: 'Component',
        file_path: 'src/App.tsx',
        dependencies: []
      }
    ]
  },
  {
    name: 'api',
    description: 'API layer',
    components: [
      {
        name: 'UserController',
        type: 'Controller',
        file_path: 'src/controllers/UserController.ts',
        dependencies: []
      }
    ]
  }
]

// Test component rendering
console.log('Mock layers:', mockLayers)
console.log('Component should render with', mockLayers.length, 'layers')

export { mockLayers }
