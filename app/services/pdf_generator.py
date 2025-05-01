"""PDF Generator service using Playwright for HTML to PDF conversion."""
import asyncio
import hashlib
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class PDFGenerator:
    """PDF Generator service for creating PDF files from HTML content.
    
    This service uses Playwright to render HTML in a headless browser 
    and convert it to a PDF document with various customization options.
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        cache_max_age: int = 3600,  # 1 hour in seconds
        cleanup_interval: int = 86400,  # 24 hours in seconds
    ) -> None:
        """Initialize the PDF Generator service.
        
        Args:
            cache_dir (Optional[str], optional): Directory for caching PDFs. If None, a temp directory is used.
            cache_max_age (int, optional): Maximum age of cache entries in seconds. Defaults to 3600 (1 hour).
            cleanup_interval (int, optional): How often to clean up old cache entries in seconds. Defaults to 86400 (24 hours).
        """
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "foglioai_pdf_cache")
        self.cache_max_age = cache_max_age
        self.cleanup_interval = cleanup_interval
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Set up basic paper sizes (width x height in points)
        self.paper_sizes = {
            "tabloid": {"width": "11in", "height": "17in"},
            "broadsheet": {"width": "13.5in", "height": "24in"},  
            "berliner": {"width": "12.4in", "height": "18.5in"},
            "letter": {"width": "8.5in", "height": "11in"},
            "a4": {"width": "8.27in", "height": "11.69in"},
            "a3": {"width": "11.69in", "height": "16.54in"},
        }
        
        # Start background cleanup task
        self._start_cleanup_task()
    
    def _start_cleanup_task(self) -> None:
        """Start the background task to clean up old cache entries."""
        async def cleanup_task():
            while True:
                await asyncio.sleep(self.cleanup_interval)
                try:
                    self.cleanup_cache()
                except Exception as e:
                    logger.error(f"Error during cache cleanup: {e}")
        
        # Run the cleanup task in the background
        asyncio.create_task(cleanup_task())
    
    def _generate_cache_key(self, html: str, options: Dict) -> str:
        """Generate a cache key for the PDF.
        
        Args:
            html (str): HTML content
            options (Dict): PDF generation options
            
        Returns:
            str: Cache key
        """
        # Create a unique hash based on the HTML content and options
        content_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
        options_hash = hashlib.sha256(str(options).encode("utf-8")).hexdigest()
        return f"{content_hash[:16]}_{options_hash[:16]}"
    
    def _get_cached_pdf_path(self, cache_key: str) -> Optional[str]:
        """Get the path to a cached PDF if it exists and is not expired.
        
        Args:
            cache_key (str): Cache key
            
        Returns:
            Optional[str]: Path to the cached PDF, or None if not cached or expired
        """
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pdf")
        
        if os.path.exists(cache_file):
            # Check if the file is not expired
            file_age = datetime.now().timestamp() - os.path.getmtime(cache_file)
            if file_age < self.cache_max_age:
                return cache_file
        
        return None
    
    def cleanup_cache(self) -> None:
        """Clean up expired cache entries."""
        now = datetime.now().timestamp()
        
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith(".pdf"):
                continue
                
            cache_file = os.path.join(self.cache_dir, filename)
            file_age = now - os.path.getmtime(cache_file)
            
            if file_age > self.cache_max_age:
                try:
                    os.remove(cache_file)
                    logger.debug(f"Removed expired cache file: {cache_file}")
                except Exception as e:
                    logger.error(f"Failed to remove cache file {cache_file}: {e}")
    
    async def generate_pdf(
        self,
        html: str,
        filename: Optional[str] = None,
        paper_size: str = "tabloid",
        display_header_footer: bool = False,
        header_template: Optional[str] = None,
        footer_template: Optional[str] = None,
        margin: Optional[Dict[str, str]] = None,
        print_background: bool = True,
        landscape: bool = False,
        scale: float = 1.0,
        prefer_css_page_size: bool = False,
        use_cache: bool = True,
    ) -> Tuple[str, bool]:
        """Generate a PDF from HTML content.
        
        Args:
            html (str): HTML content to convert to PDF
            filename (Optional[str], optional): Output filename. If None, a temp file is used.
            paper_size (str, optional): Paper size (tabloid, broadsheet, berliner, letter, a4, a3). Defaults to "tabloid".
            display_header_footer (bool, optional): Whether to display headers and footers. Defaults to False.
            header_template (Optional[str], optional): HTML template for the header. Defaults to None.
            footer_template (Optional[str], optional): HTML template for the footer. Defaults to None.
            margin (Optional[Dict[str, str]], optional): Page margins (top, right, bottom, left). Defaults to None.
            print_background (bool, optional): Whether to print background graphics. Defaults to True.
            landscape (bool, optional): Whether to use landscape orientation. Defaults to False.
            scale (float, optional): Scale of the webpage rendering (0.1-2). Defaults to 1.0.
            prefer_css_page_size (bool, optional): Give priority to CSS page size over paper_size argument. Defaults to False.
            use_cache (bool, optional): Whether to use the PDF cache. Defaults to True.
            
        Returns:
            Tuple[str, bool]: Path to the PDF file and whether it was retrieved from cache
        """
        # Default margins based on paper size
        if margin is None:
            if paper_size in ["tabloid", "broadsheet"]:
                margin = {"top": "0.5in", "right": "0.5in", "bottom": "0.5in", "left": "0.5in"}
            else:
                margin = {"top": "0.4in", "right": "0.4in", "bottom": "0.4in", "left": "0.4in"}
        
        # Get page dimensions
        page_size = self.paper_sizes.get(paper_size.lower(), self.paper_sizes["tabloid"])
        
        # Build PDF options
        pdf_options = {
            "width": page_size["width"],
            "height": page_size["height"],
            "margin": margin,
            "printBackground": print_background,
            "landscape": landscape,
            "scale": scale,
            "displayHeaderFooter": display_header_footer,
            "preferCSSPageSize": prefer_css_page_size,
        }
        
        if display_header_footer:
            if header_template:
                pdf_options["headerTemplate"] = header_template
            if footer_template:
                pdf_options["footerTemplate"] = footer_template
        
        # Generate cache key and check cache
        if use_cache:
            cache_key = self._generate_cache_key(html, pdf_options)
            cached_path = self._get_cached_pdf_path(cache_key)
            
            if cached_path:
                if filename:
                    # Copy the cached file to the requested filename
                    output_path = filename
                    with open(cached_path, "rb") as src, open(output_path, "wb") as dst:
                        dst.write(src.read())
                else:
                    output_path = cached_path
                    
                logger.debug(f"Using cached PDF: {output_path}")
                return output_path, True
        
        # Determine output path
        if filename:
            output_path = filename
        else:
            output_path = os.path.join(
                self.cache_dir, 
                f"foglioai_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            )
        
        # Generate PDF
        try:
            async with async_playwright() as playwright:
                # Launch browser
                browser = await playwright.chromium.launch()
                page = await browser.new_page()
                
                # Set content
                await page.set_content(html, wait_until="networkidle")
                
                # Wait a moment for any fonts or resources to load
                await asyncio.sleep(1)
                
                # Generate PDF
                pdf_bytes = await page.pdf(**pdf_options)
                
                # Close browser
                await browser.close()
                
                # Write PDF to file
                with open(output_path, "wb") as f:
                    f.write(pdf_bytes)
                
                # Cache the PDF if requested
                if use_cache and not filename:
                    cache_key = self._generate_cache_key(html, pdf_options)
                    cache_path = os.path.join(self.cache_dir, f"{cache_key}.pdf")
                    with open(cache_path, "wb") as f:
                        f.write(pdf_bytes)
                
                logger.debug(f"Generated PDF: {output_path}")
                return output_path, False
                
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise
    
    async def generate_newspaper_pdf(
        self, 
        html: str,
        newspaper_name: str = "FoglioAI Gazette",
        publication_date: Optional[datetime] = None,
        paper_format: str = "tabloid",
        use_cache: bool = True,
    ) -> str:
        """Generate a newspaper-formatted PDF.
        
        This is a convenience method that sets suitable defaults for newspaper PDFs.
        
        Args:
            html (str): HTML content of the newspaper
            newspaper_name (str, optional): Name of the newspaper. Defaults to "FoglioAI Gazette".
            publication_date (Optional[datetime], optional): Publication date. Defaults to current date.
            paper_format (str, optional): Paper size format. Defaults to "tabloid".
            use_cache (bool, optional): Whether to use the PDF cache. Defaults to True.
            
        Returns:
            str: Path to the generated PDF file
        """
        if publication_date is None:
            publication_date = datetime.now()
        
        date_str = publication_date.strftime("%B %d, %Y")
        
        # Create header and footer templates
        header_template = f"""
        <div style="width: 100%; font-family: 'Old Standard TT', serif; font-size: 8pt; text-align: center; color: #888;">
            {newspaper_name}
        </div>
        """
        
        footer_template = f"""
        <div style="width: 100%; font-family: 'Old Standard TT', serif; font-size: 8pt; 
             display: flex; justify-content: space-between; padding: 0 1cm;">
            <span>{date_str}</span>
            <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
        </div>
        """
        
        # Generate a filename based on the newspaper name and date
        safe_name = "".join([c if c.isalnum() else "_" for c in newspaper_name.lower()])
        date_part = publication_date.strftime("%Y%m%d")
        filename = os.path.join(self.cache_dir, f"{safe_name}_{date_part}.pdf")
        
        # Generate the PDF with newspaper-specific settings
        pdf_path, _ = await self.generate_pdf(
            html=html,
            filename=filename,
            paper_size=paper_format,
            display_header_footer=True,
            header_template=header_template,
            footer_template=footer_template,
            print_background=True,
            landscape=False,
            use_cache=use_cache
        )
        
        return pdf_path 