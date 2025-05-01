"""Tests for template renderer service."""
import uuid
from datetime import datetime

import pytest

from app.models.article import Article
from app.services.template import TemplateRenderer


@pytest.fixture
def template_renderer():
    """Template renderer fixture."""
    return TemplateRenderer()


@pytest.fixture
def sample_article():
    """Sample article fixture."""
    return Article(
        id=uuid.uuid4(),
        title="Test Article",
        content="# Test Article\n\nThis is a test article.",
        topic="Testing",
        sources=["https://example.com/test"],
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


def test_render_article_basic(template_renderer, sample_article):
    """Test basic article rendering."""
    html = template_renderer.render_article(sample_article)

    # Check basic structure
    assert "<title>Test Article</title>" in html
    assert "<h1 class=\"headline\">Test Article</h1>" in html
    assert "January 01, 2024" in html
    assert "<div class=\"sources\">" in html
    assert "https://example.com/test" in html


def test_render_article_with_style_guide(template_renderer, sample_article):
    """Test article rendering with style guide."""
    style_guide = {
        "font": "Georgia",
        "color": "#333333",
    }
    html = template_renderer.render_article(sample_article, style_guide)

    # Check style customizations
    assert "font-family: Georgia" in html
    assert "color: #333333" in html


def test_render_article_complex_content(template_renderer):
    """Test rendering article with complex content."""
    article = Article(
        id=uuid.uuid4(),
        title="Scientific Discovery",
        content="""# Scientific Discovery

[dateline]LONDON, January 1st, 1920[/dateline]

[lead]A groundbreaking discovery has been made.[/lead]

Scientists at the Royal Institution have made an extraordinary finding that challenges our understanding of physics.

> This discovery will change everything we know about science.

## Implications

The implications of this discovery are far-reaching.""",
        topic="Science",
        sources=[
            "Royal Institution Quarterly, Vol. 12",
            "Nature Journal, January 1920",
        ],
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )

    html = template_renderer.render_article(article)

    # Check structure and styling
    assert "<h1 class=\"headline\">Scientific Discovery</h1>" in html
    assert "<div class=\"dateline\">LONDON, January 1st, 1920</div>" in html
    assert "<p class=\"lead-in\">A groundbreaking discovery has been made.</p>" in html
    assert "<blockquote class=\"pullquote\">" in html
    assert "<h2 class=\"subheadline\">Implications</h2>" in html
    assert "Royal Institution Quarterly, Vol. 12" in html
    assert "Nature Journal, January 1920" in html


def test_render_article_error_handling(template_renderer):
    """Test error handling in article rendering."""
    with pytest.raises(Exception):
        template_renderer.render_article(None)  # type: ignore 