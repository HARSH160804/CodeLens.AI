import Editor from '@monaco-editor/react'
import { useApp } from '../../context/AppContext'

interface CodeViewerProps {
  code: string
  language: string
  onLineClick?: (lineNumber: number) => void
}

export function CodeViewer({ code, language, onLineClick }: CodeViewerProps) {
  const { darkMode } = useApp()

  const handleEditorMount = (editor: any) => {
    // Add click handler for line numbers
    editor.onMouseDown((e: any) => {
      if (e.target.type === 2) { // Line number gutter
        const lineNumber = e.target.position.lineNumber
        onLineClick?.(lineNumber)
      }
    })
  }

  return (
    <div className="h-full w-full">
      <Editor
        height="100%"
        language={language}
        value={code}
        theme={darkMode ? 'vs-dark' : 'light'}
        options={{
          readOnly: true,
          minimap: { enabled: true },
          fontSize: 14,
          lineNumbers: 'on',
          glyphMargin: true,
          folding: true,
          lineDecorationsWidth: 10,
          lineNumbersMinChars: 4,
          renderLineHighlight: 'all',
          scrollBeyondLastLine: false,
          automaticLayout: true,
        }}
        onMount={handleEditorMount}
      />
    </div>
  )
}
