/**
 * ExportDropdown Component
 * 
 * Dropdown menu for exporting documentation in different formats.
 * Provides Markdown and PDF export options.
 */

import { useState, useRef, useEffect } from 'react'
import { Download, FileText, FileType, ChevronDown } from 'lucide-react'

interface ExportDropdownProps {
  onExportMarkdown: () => void
  onExportPdf: () => void
}

export function ExportDropdown({ onExportMarkdown, onExportPdf }: ExportDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])
  
  const handleExport = (exportFn: () => void) => {
    exportFn()
    setIsOpen(false)
  }
  
  return (
    <div className="relative" ref={dropdownRef}>
      {/* Dropdown Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="
          inline-flex items-center gap-2 px-6 py-2.5 rounded-full font-medium
          bg-green-600 text-white hover:bg-green-700 active:bg-green-800
          transition-all duration-200
        "
      >
        <Download className="w-4 h-4" />
        <span>Export Documentation</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      
      {/* Dropdown Menu - Glassmorphism */}
      {isOpen && (
        <div 
          className="
            absolute right-0 mt-2 w-56 rounded-2xl shadow-2xl
            backdrop-blur-xl bg-white/80 dark:bg-gray-900/80
            border border-white/20 dark:border-gray-700/30
            z-50
          "
          style={{
            backdropFilter: 'blur(16px) saturate(180%)',
            WebkitBackdropFilter: 'blur(16px) saturate(180%)',
          }}
        >
          <div className="py-2">
            {/* Markdown Option */}
            <button
              onClick={() => handleExport(onExportMarkdown)}
              className="
                w-full flex items-center gap-3 px-4 py-3
                text-left text-gray-800 dark:text-gray-200
                hover:bg-white/40 dark:hover:bg-gray-800/40
                transition-all duration-200
                first:rounded-t-2xl
              "
            >
              <FileText className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              <div>
                <div className="font-medium">Export as Markdown</div>
                <div className="text-xs text-gray-600 dark:text-gray-400">Download .md file</div>
              </div>
            </button>
            
            {/* PDF Option */}
            <button
              onClick={() => handleExport(onExportPdf)}
              className="
                w-full flex items-center gap-3 px-4 py-3
                text-left text-gray-800 dark:text-gray-200
                hover:bg-white/40 dark:hover:bg-gray-800/40
                transition-all duration-200
                last:rounded-b-2xl
              "
            >
              <FileType className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              <div>
                <div className="font-medium">Export as PDF</div>
                <div className="text-xs text-gray-600 dark:text-gray-400">Download .pdf file</div>
              </div>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
