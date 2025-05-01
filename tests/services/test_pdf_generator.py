"""Tests for PDF generator service."""
import os
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from playwright.async_api import Page, Browser, BrowserContext, Playwright

from app.services.pdf_generator import PDFGenerator


@pytest.fixture
def pdf_generator():
    """Return a PDFGenerator instance with a test cache directory."""
    # Use a temporary directory for testing
    import tempfile
    test_cache_dir = os.path.join(tempfile.gettempdir(), "foglioai_pdf_test_cache")
    os.makedirs(test_cache_dir, exist_ok=True)
    
    generator = PDFGenerator(cache_dir=test_cache_dir, cache_max_age=60)
    yield generator
    
    # Cleanup test files
    for file in os.listdir(test_cache_dir):
        try:
            os.remove(os.path.join(test_cache_dir, file))
        except:
            pass
    try:
        os.rmdir(test_cache_dir)
    except:
        pass


def test_pdf_generator_init():
    """Test PDFGenerator initialization."""
    generator = PDFGenerator(cache_dir="/tmp/test_pdf")
    assert generator.cache_dir == "/tmp/test_pdf"
    assert generator.cache_max_age == 3600
    assert generator.cleanup_interval == 86400
    assert "tabloid" in generator.paper_sizes
    assert "broadsheet" in generator.paper_sizes
    assert "letter" in generator.paper_sizes
    assert "a4" in generator.paper_sizes


def test_cache_key_generation(pdf_generator):
    """Test cache key generation."""
    html = "<html><body>Test</body></html>"
    options = {"width": "11in", "height": "17in"}
    
    key1 = pdf_generator._generate_cache_key(html, options)
    assert isinstance(key1, str)
    assert len(key1) > 10
    
    # Same content and options should produce the same key
    key2 = pdf_generator._generate_cache_key(html, options)
    assert key1 == key2
    
    # Different content should produce different key
    key3 = pdf_generator._generate_cache_key(html + " ", options)
    assert key1 != key3
    
    # Different options should produce different key
    key4 = pdf_generator._generate_cache_key(html, {"width": "8.5in", "height": "11in"})
    assert key1 != key4


def test_cleanup_cache(pdf_generator):
    """Test cache cleanup."""
    # Create some test files
    import time
    
    # Current time files (shouldn't be deleted)
    test_file1 = os.path.join(pdf_generator.cache_dir, "test1.pdf")
    with open(test_file1, "w") as f:
        f.write("test1")
    
    # Expired files (should be deleted)
    test_file2 = os.path.join(pdf_generator.cache_dir, "test2.pdf")
    with open(test_file2, "w") as f:
        f.write("test2")
    
    # Set mtime to past (expired)
    old_time = time.time() - (pdf_generator.cache_max_age * 2)
    os.utime(test_file2, (old_time, old_time))
    
    # Non-PDF file (shouldn't be deleted)
    test_file3 = os.path.join(pdf_generator.cache_dir, "test3.txt")
    with open(test_file3, "w") as f:
        f.write("test3")
    os.utime(test_file3, (old_time, old_time))
    
    # Run cleanup
    pdf_generator.cleanup_cache()
    
    # Check if the expected files were deleted
    assert os.path.exists(test_file1)  # Current PDF file should exist
    assert not os.path.exists(test_file2)  # Expired PDF file should be deleted
    assert os.path.exists(test_file3)  # Non-PDF file should exist


@pytest.mark.asyncio
async def test_generate_pdf(pdf_generator):
    """Test PDF generation."""
    # Mock Playwright objects
    mock_page = AsyncMock(spec=Page)
    mock_browser = AsyncMock(spec=Browser)
    mock_browser.new_page.return_value = mock_page
    
    mock_context = AsyncMock(spec=BrowserContext)
    mock_playwright = AsyncMock(spec=Playwright)
    mock_playwright.chromium.launch.return_value = mock_browser
    
    # Mock PDF generation
    mock_page.pdf.return_value = b"PDF content"
    
    # Mock playwright context manager
    with patch("app.services.pdf_generator.async_playwright") as mock_playwright_constructor:
        mock_playwright_constructor.return_value.__aenter__.return_value = mock_playwright
        
        # Test PDF generation
        html = "<html><body>Test PDF</body></html>"
        pdf_path, from_cache = await pdf_generator.generate_pdf(
            html=html,
            paper_size="tabloid",
            print_background=True
        )
        
        # Check the result
        assert pdf_path.startswith(pdf_generator.cache_dir)
        assert pdf_path.endswith(".pdf")
        assert not from_cache
        assert os.path.exists(pdf_path)
        
        # Verify the mocks were called correctly
        mock_playwright.chromium.launch.assert_called_once()
        mock_browser.new_page.assert_called_once()
        mock_page.set_content.assert_called_once_with(html, wait_until="networkidle")
        mock_page.pdf.assert_called_once()
        
        # Clean up the generated file
        os.remove(pdf_path)


@pytest.mark.asyncio
async def test_generate_newspaper_pdf(pdf_generator):
    """Test newspaper PDF generation."""
    # Mock the generate_pdf method
    with patch.object(pdf_generator, "generate_pdf") as mock_generate_pdf:
        mock_generate_pdf.return_value = ("/tmp/test_newspaper.pdf", False)
        
        # Test newspaper PDF generation
        html = "<html><body>Test Newspaper</body></html>"
        newspaper_name = "Test Gazette"
        
        pdf_path = await pdf_generator.generate_newspaper_pdf(
            html=html,
            newspaper_name=newspaper_name,
            paper_format="tabloid"
        )
        
        # Check the result
        assert pdf_path == "/tmp/test_newspaper.pdf"
        
        # Verify the mocks were called correctly
        mock_generate_pdf.assert_called_once()
        # Verify newspaper name is in the header template
        call_args = mock_generate_pdf.call_args[1]
        assert newspaper_name in call_args["header_template"]
        assert call_args["paper_size"] == "tabloid"
        assert call_args["print_background"] is True 