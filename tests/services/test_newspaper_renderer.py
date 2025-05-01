"""Tests for the newspaper renderer service."""
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from app.models.article import Article
from app.services.newspaper_renderer import NewspaperRenderer, newspaper_renderer


@pytest.fixture
def mock_article():
    """Create a mock article for testing."""
    return Article(
        id=uuid.uuid4(),
        topic="Climate change impacts",
        title="Global Temperatures Reach Record High in Latest Measurements",
        subtitle="Scientists warn of accelerating climate trends",
        content="""
Climate scientists reported yesterday that global temperatures have reached unprecedented levels according to the latest measurements from monitoring stations around the world.

The new data, collected from over 3,000 weather stations, shows an average increase of 1.2 degrees Celsius compared to pre-industrial levels, raising concerns about the pace of climate change.

"These findings are alarming but not unexpected," said Dr. Maria Chen, lead researcher at the Global Climate Institute. "We've been observing this trend for decades, but the acceleration we're seeing now suggests we may reach critical thresholds sooner than previously projected."

The report highlights several regions experiencing more severe impacts:

- Arctic zones showing temperature increases at twice the global average
- Coastal areas facing rising sea levels and increased flooding
- Agricultural regions experiencing more frequent drought conditions

Policy makers are being urged to accelerate emissions reduction targets in response to the new data. The findings will be presented at the upcoming UN Climate Summit next month.
        """,
        outline=None,
        style_guide={"tone": "vintage"},
        status="published",
        created_at=datetime.now(timezone.utc),
    )


def test_newspaper_renderer_initialization():
    """Test that the newspaper renderer initializes correctly."""
    renderer = NewspaperRenderer()
    assert renderer.env is not None
    assert "vintage_date" in renderer.env.filters
    assert "vintage_time" in renderer.env.filters
    assert "format_headline" in renderer.env.filters
    assert "format_byline" in renderer.env.filters


def test_vintage_date_format():
    """Test the vintage date formatting."""
    renderer = NewspaperRenderer()
    
    # Test datetime object
    test_date = datetime(1929, 10, 24, 12, 30)
    formatted = renderer.vintage_date_format(test_date)
    assert formatted == "October 24, 1929"
    
    # Test string date
    formatted = renderer.vintage_date_format("1929-10-24T12:30:00")
    assert formatted == "October 24, 1929"
    
    # Test invalid string
    formatted = renderer.vintage_date_format("not a date")
    assert formatted == "not a date"


def test_vintage_time_format():
    """Test the vintage time formatting."""
    renderer = NewspaperRenderer()
    
    # Test morning time
    morning_time = datetime(1929, 10, 24, 10, 30)
    formatted = renderer.vintage_time_format(morning_time)
    assert formatted == "10:30 o'clock A.M."
    
    # Test afternoon time
    afternoon_time = datetime(1929, 10, 24, 15, 45)
    formatted = renderer.vintage_time_format(afternoon_time)
    assert formatted == "3:45 o'clock P.M."
    
    # Test midnight
    midnight = datetime(1929, 10, 24, 0, 0)
    formatted = renderer.vintage_time_format(midnight)
    assert formatted == "12:00 o'clock A.M."
    
    # Test noon
    noon = datetime(1929, 10, 24, 12, 0)
    formatted = renderer.vintage_time_format(noon)
    assert formatted == "12:00 o'clock P.M."


def test_format_headline():
    """Test headline formatting."""
    renderer = NewspaperRenderer()
    
    headline = "Global temperatures reach record high"
    formatted = renderer.format_headline(headline)
    assert formatted == "GLOBAL TEMPERATURES REACH RECORD HIGH"


def test_format_byline():
    """Test byline formatting."""
    renderer = NewspaperRenderer()
    
    # Test without "By" prefix
    byline = "John Smith"
    formatted = renderer.format_byline(byline)
    assert formatted == "By John Smith"
    
    # Test with "By" prefix
    byline = "By Jane Doe"
    formatted = renderer.format_byline(byline)
    assert formatted == "By Jane Doe"
    
    # Test empty byline
    formatted = renderer.format_byline("")
    assert formatted == ""


def test_create_dateline():
    """Test dateline creation."""
    renderer = NewspaperRenderer()
    
    location = "New York"
    date = datetime(1929, 10, 24)
    
    dateline = renderer.create_dateline(location, date)
    assert dateline == "NEW YORK, OCT. 24 —"


@pytest.mark.asyncio
async def test_render_article_with_inline_css(mock_article):
    """Test article rendering with inline CSS."""
    with patch("app.services.newspaper_renderer.convert_to_html") as mock_convert:
        mock_convert.return_value = "<p>Test article content</p>"
        
        renderer = NewspaperRenderer()
        html = renderer.render_article(mock_article)
        
        # Basic verification
        assert html is not None
        assert isinstance(html, str)
        assert len(html) > 0
        
        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")
        
        # Check basic structure
        assert soup.find("title").text.strip() == f"{mock_article.title} - FoglioAI Gazette"
        assert soup.find("h1", class_="article-title").text.strip() == mock_article.title
        assert soup.find("div", class_="article-subtitle").text.strip() == mock_article.subtitle
        
        # Verify inline CSS is used (style tag exists)
        assert soup.select("head style") is not None
        # Verify no external CSS link
        assert not soup.select('link[rel="stylesheet"]')


@pytest.mark.asyncio
async def test_render_article_with_external_css(mock_article):
    """Test article rendering with external CSS."""
    with patch("app.services.newspaper_renderer.convert_to_html") as mock_convert:
        mock_convert.return_value = "<p>Test article content</p>"
        
        renderer = NewspaperRenderer()
        html = renderer.render_article(
            mock_article, 
            use_external_css=True, 
            css_path="/custom/path/styles.css"
        )
        
        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")
        
        # Check basic structure
        assert soup.find("title").text.strip() == f"{mock_article.title} - FoglioAI Gazette"
        
        # Verify external CSS is used
        css_link = soup.select('link[rel="stylesheet"]')
        assert css_link is not None
        assert css_link[0]["href"] == "/custom/path/styles.css"
        
        # Verify no inline style tag with CSS
        assert not soup.select("head style")


@pytest.mark.asyncio
async def test_render_front_page():
    """Test front page rendering."""
    headline_article = {
        "title": "Global Temperatures Reach Record High",
        "subtitle": "Scientists warn of accelerating climate trends",
        "byline": "Dr. Jane Smith",
        "date": "October 24, 2023",
        "summary": "<p>Climate scientists reported yesterday that global temperatures have reached unprecedented levels according to the latest measurements.</p>",
        "url": "/article/1",
    }
    
    secondary_articles = [
        {
            "title": "Local Council Approves New Transit Plan",
            "byline": "John Doe",
            "date": "October 24, 2023",
            "summary": "<p>The city council unanimously approved a new public transit expansion.</p>",
            "url": "/article/2",
        }
    ]
    
    renderer = NewspaperRenderer()
    html = renderer.render_front_page(
        headline_article=headline_article,
        secondary_articles=secondary_articles,
        newspaper_name="The Daily Chronicle"
    )
    
    # Basic verification
    assert html is not None
    assert isinstance(html, str)
    assert len(html) > 0
    
    # Parse HTML
    soup = BeautifulSoup(html, "html.parser")
    
    # Check structure
    assert soup.find("title").text.strip() == "The FoglioAI Gazette - Front Page"
    assert soup.find("div", class_="newspaper-name").text.strip() == "The Daily Chronicle"
    assert soup.find("h1", class_="headline-title").text.strip() == "Global Temperatures Reach Record High"
    assert soup.find("h2", class_="secondary-title").text.strip() == "Local Council Approves New Transit Plan"
    
    # Verify inline CSS is used by default
    assert soup.select("head style") is not None


@pytest.mark.asyncio
async def test_render_front_page_with_external_css():
    """Test front page rendering with external CSS."""
    headline_article = {
        "title": "Global Temperatures Reach Record High",
        "subtitle": "Scientists warn of accelerating climate trends",
        "byline": "Dr. Jane Smith",
        "date": "October 24, 2023",
        "summary": "<p>Climate scientists reported yesterday that global temperatures have reached unprecedented levels.</p>",
        "url": "/article/1",
    }
    
    renderer = NewspaperRenderer()
    html = renderer.render_front_page(
        headline_article=headline_article,
        newspaper_name="The Daily Chronicle",
        use_external_css=True
    )
    
    # Parse HTML
    soup = BeautifulSoup(html, "html.parser")
    
    # Verify external CSS is used
    css_link = soup.select('link[rel="stylesheet"]')
    assert css_link is not None
    # Default path should be used
    assert css_link[0]["href"] == "/static/css/vintage-newspaper.css"
    
    # Verify no inline style tag with CSS
    assert not soup.select("head style")


def test_global_renderer_instance():
    """Test that the global renderer instance exists."""
    assert newspaper_renderer is not None
    assert isinstance(newspaper_renderer, NewspaperRenderer) 