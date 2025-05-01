"""Tests for template helper functions."""
import re
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from markupsafe import Markup

from app.models.article import Article
from app.models.article_run import Citation
from app.services.template_helpers import TemplateManager


@pytest.fixture
def template_manager():
    """Return a TemplateManager instance."""
    return TemplateManager()


@pytest.fixture
def sample_article():
    """Return a sample article."""
    return Article(
        id=uuid4(),
        title="The Great Depression: A Historical Perspective",
        subtitle="Economic Lessons from the 1929 Crash",
        author="John Smith",
        content=(
            "# The Great Depression\n\n"
            "[dateline]NEW YORK, Oct. 24[/dateline]\n\n"
            "[lead]The stock market crashed today, marking the beginning of what economists are calling a severe economic downturn.[/lead]\n\n"
            "## Background\n\n"
            "The 1920s were a period of great prosperity in America, often called the 'Roaring Twenties'. "
            "However, this prosperity was built on shaky foundations.\n\n"
            "## Causes\n\n"
            "Many factors contributed to the crash:\n\n"
            "1. Excessive speculation in the stock market\n"
            "2. Weak banking systems\n"
            "3. Industrial overproduction\n\n"
            "![Stock market crash](https://example.com/crash.jpg)\n\n"
            "## Impact\n\n"
            "The crash had far-reaching consequences, including:\n\n"
            "- Widespread unemployment\n"
            "- Bank failures\n"
            "- Global economic downturn\n\n"
            "As President Hoover stated: 'Prosperity is just around the corner.'"
        ),
        created_at=datetime(1929, 10, 24, 14, 30),
        updated_at=datetime(1929, 10, 24, 15, 45),
        status="COMPLETED",
        error=None,
    )


@pytest.fixture
def sample_citations():
    """Return sample citations."""
    return [
        Citation(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            url="https://example.com/article1",
            title="The Stock Market Crash of 1929",
            author="Jane Doe",
            published_at=datetime(1930, 1, 15),
            excerpt="The crash of 1929 marked the beginning of a decade-long economic depression.",
            access_timestamp=datetime(2023, 5, 1),
        ),
        Citation(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            url="https://example.com/article2",
            title="Herbert Hoover and the Great Depression",
            author="John Brown",
            published_at=datetime(1932, 3, 10),
            excerpt="President Hoover's policies were insufficient to combat the economic crisis.",
            access_timestamp=datetime(2023, 5, 2),
        ),
    ]


class TestDateFormatting:
    """Test date formatting functions."""

    def test_vintage_date_format(self, template_manager):
        """Test vintage date formatting."""
        date = datetime(1929, 10, 24)
        formatted = template_manager.vintage_date_format(date)
        assert formatted == "October 24, 1929"

        # Test with string input
        formatted = template_manager.vintage_date_format("1929-10-24T00:00:00")
        assert formatted == "October 24, 1929"

        # Test with invalid string
        invalid_date = "not a date"
        formatted = template_manager.vintage_date_format(invalid_date)
        assert formatted == invalid_date

    def test_vintage_time_format(self, template_manager):
        """Test vintage time formatting."""
        # Morning time
        date = datetime(1929, 10, 24, 9, 30)
        formatted = template_manager.vintage_time_format(date)
        assert formatted == "9:30 o'clock A.M."

        # Afternoon time
        date = datetime(1929, 10, 24, 14, 45)
        formatted = template_manager.vintage_time_format(date)
        assert formatted == "2:45 o'clock P.M."

        # Midnight
        date = datetime(1929, 10, 24, 0, 0)
        formatted = template_manager.vintage_time_format(date)
        assert formatted == "12:00 o'clock A.M."

        # Noon
        date = datetime(1929, 10, 24, 12, 0)
        formatted = template_manager.vintage_time_format(date)
        assert formatted == "12:00 o'clock P.M."

    def test_create_dateline(self, template_manager):
        """Test dateline creation."""
        date = datetime(1929, 10, 24)
        dateline = template_manager.create_dateline("New York", date)
        assert dateline == "NEW YORK, OCT. 24 —"

        # Test with default date (current date)
        dateline = template_manager.create_dateline("Chicago")
        today = datetime.now()
        expected_month = today.strftime("%b").upper()
        expected_day = today.day
        assert dateline == f"CHICAGO, {expected_month}. {expected_day} —"


class TestTextFormatting:
    """Test text formatting functions."""

    def test_format_headline(self, template_manager):
        """Test headline formatting."""
        headline = "Stock Market Crashes in Historic Plunge"
        formatted = template_manager.format_headline(headline)
        assert formatted == "STOCK MARKET CRASHES IN HISTORIC PLUNGE"

    def test_format_byline(self, template_manager):
        """Test byline formatting."""
        # Without "By" prefix
        byline = "John Smith"
        formatted = template_manager.format_byline(byline)
        assert formatted == "By John Smith"

        # With "By" prefix already
        byline = "By Jane Doe"
        formatted = template_manager.format_byline(byline)
        assert formatted == byline

        # Empty byline
        formatted = template_manager.format_byline("")
        assert formatted == ""

    def test_format_title(self, template_manager):
        """Test title formatting."""
        # Standard title
        title = "the great depression and its impact on america"
        formatted = template_manager.format_title(title)
        assert formatted == "The Great Depression and Its Impact on America"

        # Title with prepositions and articles
        title = "a view from the top of the market"
        formatted = template_manager.format_title(title)
        assert formatted == "A View from the Top of the Market"

        # Title with capitalize_all=True
        formatted = template_manager.format_title(title, capitalize_all=True)
        assert formatted == "A View From The Top Of The Market"

        # Empty title
        formatted = template_manager.format_title("")
        assert formatted == ""

    def test_format_lead_paragraph(self, template_manager):
        """Test lead paragraph formatting."""
        # Short paragraph (4 words or less)
        short_lead = "Markets crashed this morning."
        formatted = template_manager.format_lead_paragraph(short_lead)
        assert formatted == f'<span class="small-caps">{short_lead}</span>'

        # Longer paragraph
        long_lead = "The stock market crashed this morning, sending waves of panic across Wall Street."
        formatted = template_manager.format_lead_paragraph(long_lead)
        assert "small-caps" in formatted
        assert "The stock market crashed this" in formatted
        assert "sending waves of panic across Wall Street." in formatted
        assert formatted.count("span") == 2  # Opening and closing tags

    def test_small_caps(self, template_manager):
        """Test small caps formatting."""
        text = "This is small caps text"
        formatted = template_manager.small_caps(text)
        assert formatted == f'<span class="small-caps">{text}</span>'


class TestLayoutHelpers:
    """Test layout helper functions."""

    def test_split_into_columns(self, template_manager):
        """Test content splitting into columns."""
        # Create test HTML with multiple paragraphs
        paragraphs = ["<p>Paragraph 1</p>", "<p>Paragraph 2</p>", "<p>Paragraph 3</p>", 
                      "<p>Paragraph 4</p>", "<p>Paragraph 5</p>", "<p>Paragraph 6</p>"]
        html = "".join(paragraphs)

        # Split into 2 columns
        columns = template_manager.split_into_columns(html, 2)
        assert len(columns) == 2
        assert "Paragraph 1" in columns[0]
        assert "Paragraph 4" in columns[1]

        # Split into 3 columns
        columns = template_manager.split_into_columns(html, 3)
        assert len(columns) == 3
        assert "Paragraph 1" in columns[0]
        assert "Paragraph 3" in columns[1]
        assert "Paragraph 5" in columns[2]

        # Single column
        columns = template_manager.split_into_columns(html, 1)
        assert len(columns) == 1
        assert html == columns[0]

        # Empty content
        columns = template_manager.split_into_columns("", 2)
        assert len(columns) == 1
        assert columns[0] == ""

    def test_word_count(self, template_manager):
        """Test word counting."""
        # Simple text
        text = "This is a test sentence with eight words."
        count = template_manager.word_count(text)
        assert count == 8

        # HTML content
        html = "<p>This is a <strong>test</strong> with <em>HTML</em> tags.</p>"
        count = template_manager.word_count(html)
        assert count == 7

        # Empty text
        count = template_manager.word_count("")
        assert count == 0


class TestCitationFormatting:
    """Test citation formatting functions."""

    def test_format_citation(self, template_manager, sample_citations):
        """Test single citation formatting."""
        citation = sample_citations[0]
        formatted = template_manager.format_citation(citation)

        # Check it's a Markup instance (safe HTML)
        assert isinstance(formatted, Markup)

        # Check content
        html_str = str(formatted)
        assert 'class="citation"' in html_str
        assert citation.title in html_str
        assert citation.url in html_str
        assert citation.excerpt in html_str
        assert "January 15, 1930" in html_str  # Formatted date

    def test_format_citation_list(self, template_manager, sample_citations):
        """Test citation list formatting."""
        formatted = template_manager.format_citation_list(sample_citations)

        # Check it's a Markup instance
        assert isinstance(formatted, Markup)

        # Check content
        html_str = str(formatted)
        assert 'class="citations"' in html_str
        assert 'class="citations-heading"' in html_str
        assert "Sources" in html_str
        assert sample_citations[0].title in html_str
        assert sample_citations[1].title in html_str

        # Empty list
        empty = template_manager.format_citation_list([])
        assert empty == ""


class TestTemplateConditions:
    """Test template condition functions."""

    def test_is_feature_article(self, template_manager, sample_article):
        """Test feature article detection."""
        # Sample article is a feature (has subtitle and long content)
        assert template_manager.is_feature_article(sample_article) is True

        # Create a non-feature article (no subtitle)
        non_feature = sample_article.copy(deep=True)
        non_feature.subtitle = None
        assert template_manager.is_feature_article(non_feature) is False

        # Create a non-feature article (short content)
        short_article = sample_article.copy(deep=True)
        short_article.content = "This is a very short article."
        assert template_manager.is_feature_article(short_article) is False

    def test_has_image(self, template_manager, sample_article):
        """Test image detection."""
        # Sample article has an image
        assert template_manager.has_image(sample_article) is True

        # Create an article without images
        no_image = sample_article.copy(deep=True)
        no_image.content = "This article has no images."
        assert template_manager.has_image(no_image) is False

    def test_is_long_article(self, template_manager, sample_article):
        """Test long article detection."""
        # Sample article is long
        assert template_manager.is_long_article(sample_article) is True

        # Create a short article
        short_article = sample_article.copy(deep=True)
        short_article.content = "This is a very short article."
        assert template_manager.is_long_article(short_article) is False


class TestSpecialFormatting:
    """Test special formatting functions."""

    def test_format_pull_quote(self, template_manager):
        """Test pull quote formatting."""
        quote = "Prosperity is just around the corner."
        attribution = "Herbert Hoover"
        
        # With attribution
        formatted = template_manager.format_pull_quote(quote, attribution)
        html_str = str(formatted)
        assert 'class="pullquote"' in html_str
        assert quote in html_str
        assert attribution in html_str
        
        # Without attribution
        formatted = template_manager.format_pull_quote(quote)
        html_str = str(formatted)
        assert 'class="pullquote"' in html_str
        assert quote in html_str
        assert "pullquote-attribution" not in html_str

    def test_generate_table_of_contents(self, template_manager):
        """Test table of contents generation."""
        # Create HTML with headers
        html = (
            "<h2>Introduction</h2><p>Content</p>"
            "<h2>First Section</h2><p>More content</p>"
            "<h3>Subsection A</h3><p>Sub-content</p>"
            "<h3>Subsection B</h3><p>More sub-content</p>"
            "<h2>Conclusion</h2><p>Final content</p>"
        )
        
        toc = template_manager.generate_table_of_contents(html)
        html_str = str(toc)
        
        # Check structure
        assert 'class="table-of-contents"' in html_str
        assert "In This Edition" in html_str
        
        # Check content
        assert "Introduction" in html_str
        assert "First Section" in html_str
        assert "Subsection A" in html_str
        assert "Subsection B" in html_str
        assert "Conclusion" in html_str
        
        # Check links
        assert 'href="#introduction"' in html_str
        assert 'href="#first-section"' in html_str
        assert 'href="#subsection-a"' in html_str
        
        # Empty content
        empty_toc = template_manager.generate_table_of_contents("<p>No headers here</p>")
        assert empty_toc == ""

    def test_render_figure(self, template_manager):
        """Test figure rendering."""
        image_url = "https://example.com/image.jpg"
        caption = "Stock market traders in panic, 1929"
        
        # Basic figure
        figure = template_manager.render_figure(image_url, caption)
        html_str = str(figure)
        
        assert 'class="article-figure"' in html_str
        assert image_url in html_str
        assert caption in html_str
        assert "<figcaption>" in html_str
        
        # Figure with custom attributes
        figure = template_manager.render_figure(
            image_url, 
            caption, 
            alt_text="Stock market crash photo",
            width="800",
            height="600",
            css_class="vintage-photo"
        )
        html_str = str(figure)
        
        assert 'class="vintage-photo"' in html_str
        assert 'alt="Stock market crash photo"' in html_str
        assert 'width="800"' in html_str
        assert 'height="600"' in html_str
        
        # Figure without caption
        figure = template_manager.render_figure(image_url)
        html_str = str(figure)
        assert "<figcaption>" not in html_str

    def test_generate_article_metadata(self, template_manager, sample_article):
        """Test article metadata generation."""
        metadata = template_manager.generate_article_metadata(sample_article)
        
        assert "The Great Depression: A Historical Perspective" in metadata["title"]
        assert "FoglioAI Gazette" in metadata["title"]
        assert metadata["description"] == "Economic Lessons from the 1929 Crash"
        assert metadata["author"] == "John Smith"
        assert metadata["date"] == "October 24, 1929"
        
        # Test with custom newspaper name
        metadata = template_manager.generate_article_metadata(sample_article, "The Daily Chronicle")
        assert "The Daily Chronicle" in metadata["title"]
        
        # Test with no subtitle (should use content excerpt)
        no_subtitle = sample_article.copy(deep=True)
        no_subtitle.subtitle = None
        metadata = template_manager.generate_article_metadata(no_subtitle)
        assert len(metadata["description"]) <= 153  # Content excerpt + "..."
        assert metadata["description"].endswith("...")


class TestTemplateRendering:
    """Test template rendering functions."""

    def test_get_template(self, template_manager):
        """Test template retrieval."""
        # This test will fail if the template doesn't exist
        template = template_manager.get_template("newspaper/article.html")
        assert template is not None

    def test_render_template(self, template_manager):
        """Test basic template rendering."""
        # Create a simple test template
        import tempfile
        import shutil
        
        # Create a temporary template directory
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Create a test template
            test_template_dir = temp_dir / "templates"
            test_template_dir.mkdir()
            
            with open(test_template_dir / "test.html", "w") as f:
                f.write("<h1>{{ title }}</h1><p>{{ content }}</p>")
            
            # Create a template manager with the test directory
            test_manager = TemplateManager(str(test_template_dir))
            
            # Render the template
            rendered = test_manager.render_template(
                "test.html", 
                title="Test Title", 
                content="Test Content"
            )
            
            assert "<h1>Test Title</h1>" in rendered
            assert "<p>Test Content</p>" in rendered
            
        finally:
            # Clean up
            shutil.rmtree(temp_dir)

    def test_render_article(self, template_manager, sample_article, sample_citations, monkeypatch):
        """Test article rendering."""
        # Mock convert_to_html to avoid template dependency
        def mock_convert(*args, **kwargs):
            return "<p>Converted HTML content</p>"
        
        monkeypatch.setattr("app.services.template_helpers.convert_to_html", mock_convert)
        
        # Mock render_template to avoid actual template rendering
        def mock_render(self, template_name, **context):
            # Check that the context contains the expected keys
            assert "article" in context
            assert "article_html" in context
            assert "metadata" in context
            assert "newspaper_name" in context
            return f"Rendered {template_name} with {len(context)} context items"
        
        monkeypatch.setattr(TemplateManager, "render_template", mock_render)
        
        # Test article rendering
        rendered = template_manager.render_article(
            sample_article,
            template_name="newspaper/article.html",
            citations=sample_citations,
            newspaper_name="Test Gazette"
        )
        
        assert "Rendered newspaper/article.html" in rendered
        assert "context items" in rendered 