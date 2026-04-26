"""
Export Service - Documentation format conversion and delivery

Converts stored documentation to requested formats (Markdown, PDF)
with caching for performance optimization.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from io import BytesIO

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Raised when documentation doesn't exist."""
    pass


class ConversionError(Exception):
    """Raised when format conversion fails."""
    pass


class ExportService:
    """
    Convert stored documentation to requested formats and deliver for download.
    
    Supports:
    - Markdown export (passthrough)
    - PDF export (markdown → HTML → PDF via weasyprint)
    - In-memory caching for PDF exports (1 hour TTL)
    """
    
    # In-memory PDF cache with TTL
    _pdf_cache: Dict[str, Tuple[bytes, datetime]] = {}
    CACHE_TTL_HOURS = 1
    
    def __init__(self, store):
        """
        Initialize ExportService.
        
        Args:
            store: DocumentationStore instance
        """
        self.store = store
    
    def _get_cached_pdf(self, repo_id: str, content_hash: str) -> Optional[bytes]:
        """
        Retrieve cached PDF if available and not expired.
        
        Args:
            repo_id: Repository identifier
            content_hash: Content hash for cache validation
            
        Returns:
            Cached PDF bytes or None
        """
        cache_key = f"{repo_id}:{content_hash}"
        
        if cache_key in self._pdf_cache:
            pdf_bytes, timestamp = self._pdf_cache[cache_key]
            
            # Check if cache is still valid
            if datetime.utcnow() - timestamp < timedelta(hours=self.CACHE_TTL_HOURS):
                logger.info(f"PDF cache hit for {repo_id}")
                return pdf_bytes
            else:
                # Remove expired cache entry
                del self._pdf_cache[cache_key]
                logger.info(f"PDF cache expired for {repo_id}")
        
        return None
    
    def _cache_pdf(self, repo_id: str, content_hash: str, pdf_bytes: bytes) -> None:
        """
        Cache PDF in memory with timestamp.
        
        Args:
            repo_id: Repository identifier
            content_hash: Content hash for cache key
            pdf_bytes: PDF content to cache
        """
        cache_key = f"{repo_id}:{content_hash}"
        self._pdf_cache[cache_key] = (pdf_bytes, datetime.utcnow())
        logger.info(f"Cached PDF for {repo_id}")
    
    def _markdown_to_html(self, markdown_content: str) -> str:
        """
        Convert markdown to HTML with styling.
        
        Args:
            markdown_content: Markdown string
            
        Returns:
            HTML string with CSS styling
        """
        try:
            import markdown
            from markdown.extensions import tables, fenced_code, toc, codehilite
            
            # Convert markdown to HTML
            html_body = markdown.markdown(
                markdown_content,
                extensions=['tables', 'fenced_code', 'toc', 'codehilite']
            )
            
            # CSS styling for professional PDF output
            css = """
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-family: 'Helvetica', 'Arial', sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #333;
            }
            h1 {
                font-size: 24pt;
                margin-top: 20pt;
                margin-bottom: 10pt;
                color: #1a1a1a;
                border-bottom: 2px solid #e0e0e0;
                padding-bottom: 5pt;
            }
            h2 {
                font-size: 18pt;
                margin-top: 15pt;
                margin-bottom: 8pt;
                color: #2a2a2a;
            }
            h3 {
                font-size: 14pt;
                margin-top: 12pt;
                margin-bottom: 6pt;
                color: #3a3a3a;
            }
            p {
                margin-bottom: 8pt;
            }
            code {
                font-family: 'Courier New', 'Consolas', monospace;
                background-color: #f4f4f4;
                padding: 2px 4px;
                border-radius: 3px;
                font-size: 10pt;
            }
            pre {
                background-color: #f8f8f8;
                padding: 10px;
                border-left: 3px solid #ccc;
                overflow-x: auto;
                margin: 10pt 0;
                border-radius: 3px;
            }
            pre code {
                background-color: transparent;
                padding: 0;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 10pt 0;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
                font-weight: bold;
            }
            ul, ol {
                margin-bottom: 8pt;
                padding-left: 20pt;
            }
            li {
                margin-bottom: 4pt;
            }
            blockquote {
                border-left: 4px solid #ddd;
                padding-left: 10pt;
                margin-left: 0;
                color: #666;
            }
            """
            
            # Combine into full HTML document
            full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>{css}</style>
</head>
<body>
    {html_body}
</body>
</html>"""
            
            return full_html
            
        except Exception as e:
            logger.error(f"Markdown to HTML conversion failed: {e}")
            raise ConversionError(f"Failed to convert markdown to HTML: {str(e)}")
    
    def _html_to_pdf(self, html_content: str) -> bytes:
        """
        Convert HTML to PDF using reportlab (Lambda-compatible).
        
        Args:
            html_content: HTML string with CSS
            
        Returns:
            PDF bytes
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from html.parser import HTMLParser
            import re
            
            # Simple HTML parser to extract text content
            class HTMLTextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text_parts = []
                    self.in_heading = False
                    self.heading_level = 0
                    
                def handle_starttag(self, tag, attrs):
                    if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        self.in_heading = True
                        self.heading_level = int(tag[1])
                    
                def handle_endtag(self, tag):
                    if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        self.in_heading = False
                        self.heading_level = 0
                    elif tag in ['p', 'div', 'br']:
                        self.text_parts.append(('paragraph', ''))
                        
                def handle_data(self, data):
                    text = data.strip()
                    if text:
                        if self.in_heading:
                            self.text_parts.append((f'heading{self.heading_level}', text))
                        else:
                            self.text_parts.append(('text', text))
            
            # Parse HTML
            parser = HTMLTextExtractor()
            parser.feed(html_content)
            
            # Create PDF buffer
            pdf_buffer = BytesIO()
            
            # Create PDF document
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            
            # Create custom styles for headings
            heading_styles = {}
            for i in range(1, 7):
                heading_styles[f'heading{i}'] = ParagraphStyle(
                    f'Heading{i}',
                    parent=styles['Heading1'],
                    fontSize=20 - (i * 2),
                    spaceAfter=12,
                    spaceBefore=12
                )
            
            # Build story (content)
            story = []
            
            for part_type, text in parser.text_parts:
                if part_type.startswith('heading'):
                    style = heading_styles.get(part_type, styles['Heading1'])
                    story.append(Paragraph(text, style))
                elif part_type == 'text' and text:
                    story.append(Paragraph(text, styles['BodyText']))
                elif part_type == 'paragraph':
                    story.append(Spacer(1, 0.2 * inch))
            
            # Build PDF
            doc.build(story)
            
            # Get PDF bytes
            pdf_bytes = pdf_buffer.getvalue()
            
            logger.info(f"Generated PDF ({len(pdf_bytes)} bytes)")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"HTML to PDF conversion failed: {e}")
            raise ConversionError(f"Failed to convert HTML to PDF: {str(e)}")
    
    async def export_markdown(self, repo_id: str) -> bytes:
        """
        Export documentation as markdown.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            Raw markdown bytes for download
            
        Raises:
            NotFoundError: If documentation doesn't exist
        """
        try:
            # Retrieve documentation from store
            doc_record = await self.store.get(repo_id)
            
            if not doc_record or 'content' not in doc_record:
                raise NotFoundError(f"Documentation not found for repository {repo_id}")
            
            # Return markdown as bytes
            markdown_bytes = doc_record['content'].encode('utf-8')
            logger.info(f"Exported markdown for {repo_id} ({len(markdown_bytes)} bytes)")
            return markdown_bytes
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Markdown export failed for {repo_id}: {e}")
            raise Exception(f"Export failed: {str(e)}")
    
    async def export_pdf(self, repo_id: str) -> bytes:
        """
        Export documentation as PDF.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            PDF bytes for download
            
        Raises:
            NotFoundError: If documentation doesn't exist
            ConversionError: If PDF conversion fails
        """
        try:
            # Retrieve documentation from store
            doc_record = await self.store.get(repo_id)
            
            if not doc_record or 'content' not in doc_record:
                raise NotFoundError(f"Documentation not found for repository {repo_id}")
            
            content_hash = doc_record.get('content_hash', '')
            
            # Check cache first
            cached_pdf = self._get_cached_pdf(repo_id, content_hash)
            if cached_pdf:
                return cached_pdf
            
            # Convert markdown to HTML
            html_content = self._markdown_to_html(doc_record['content'])
            
            # Convert HTML to PDF
            pdf_bytes = self._html_to_pdf(html_content)
            
            # Cache the PDF
            self._cache_pdf(repo_id, content_hash, pdf_bytes)
            
            logger.info(f"Exported PDF for {repo_id} ({len(pdf_bytes)} bytes)")
            return pdf_bytes
            
        except (NotFoundError, ConversionError):
            raise
        except Exception as e:
            logger.error(f"PDF export failed for {repo_id}: {e}")
            raise ConversionError(f"PDF export failed: {str(e)}")
