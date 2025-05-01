"""Tests for markdown conversion utilities."""
import uuid
from datetime import datetime

import pytest

from app.models.article_run import Citation
from app.utils.markdown import convert_to_html, process_images, render_citations


@pytest.fixture
def sample_citation() -> Citation:
    """Sample citation fixture."""
    return Citation(
        id=uuid.uuid4(),
        url="https://example.com/article",
        title="Test Article",
        excerpt="This is a test excerpt.",
        published_at=datetime(2024, 1, 1),
    )


def test_basic_markdown_conversion():
    """Test basic markdown to HTML conversion."""
    markdown = "# Test Title\n\nThis is a test paragraph."
    html = convert_to_html(markdown)

    assert "<h1>Test Title</h1>" in html
    assert '<p><span class="dropcap">T</span><span>his is a test paragraph.</span></p>' in html


def test_dateline_conversion():
    """Test dateline tag conversion."""
    markdown = "[dateline]NEW YORK, March 15th[/dateline]\n\nTest content."
    html = convert_to_html(markdown)

    assert '<div class="dateline">NEW YORK, March 15th</div>' in html


def test_lead_in_conversion():
    """Test lead-in paragraph conversion."""
    markdown = "[lead]This is a lead paragraph.[/lead]\n\nRegular paragraph."
    html = convert_to_html(markdown)

    assert '<p class="lead-in">This is a lead paragraph.</p>' in html
    assert '<p><span class="dropcap">R</span><span>egular paragraph.</span></p>' in html


def test_image_processing():
    """Test image markdown processing."""
    markdown = "![Test Image](test.jpg)"
    html = convert_to_html(markdown)

    assert '<figure class="article-figure">' in html
    assert '<img src="test.jpg" alt="Test Image">' in html
    assert "<figcaption>Test Image</figcaption>" in html


def test_typography_enhancements():
    """Test typographic enhancements."""
    markdown = 'A "quoted" text with -- dashes... and more.'
    html = convert_to_html(markdown)

    assert '"quoted"' in html
    assert "—" in html  # em dash
    assert "…" in html  # ellipsis


def test_citation_rendering(sample_citation):
    """Test citation rendering."""
    html = convert_to_html("Test content", citations=[sample_citation])

    assert '<div class="citations">' in html
    assert "<h2>Sources</h2>" in html
    assert sample_citation.title in html
    assert sample_citation.url in html
    assert sample_citation.excerpt in html
    assert "January 01, 2024" in html


def test_multiple_citations(sample_citation):
    """Test rendering multiple citations."""
    citations = [
        sample_citation,
        Citation(
            id=uuid.uuid4(),
            url="https://example.com/article2",
            title="Another Article",
            excerpt="Another test excerpt.",
            published_at=datetime(2024, 1, 2),
        ),
    ]
    html = convert_to_html("Test content", citations=citations)

    assert html.count('<li class="citation">') == 2
    assert "Another Article" in html
    assert "January 02, 2024" in html


def test_style_guide_application():
    """Test style guide application."""
    style_guide = {
        "font": "Times New Roman",
        "color": "#333333",
    }
    html = convert_to_html("Test content", style_guide=style_guide)

    assert "Test content" in html


def test_complex_markdown():
    """Test complex markdown with multiple features."""
    markdown = """[dateline]NEW YORK, March 15th[/dateline]

# Breaking News

[lead]In a stunning development...[/lead]

Regular paragraph with "quotes" and -- dashes.

![Important Image](image.jpg)

> Notable quote here

1. First point
2. Second point

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
"""
    html = convert_to_html(markdown)

    assert '<div class="dateline">' in html
    assert "<h1>Breaking News</h1>" in html
    assert '<p class="lead-in">' in html
    assert '<figure class="article-figure">' in html
    assert "<blockquote>" in html
    assert "<table>" in html
    assert "<ol>" in html 