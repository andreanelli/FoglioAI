"""Template helper functions for the vintage newspaper renderer."""
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from markupsafe import Markup

from app.models.article import Article
from app.models.article_run import Citation
from app.utils.markdown import convert_to_html

logger = logging.getLogger(__name__)


class TemplateManager:
    """Template manager class for the vintage newspaper renderer."""

    def __init__(self, template_dir: Optional[str] = None) -> None:
        """Initialize the template manager.

        Args:
            template_dir (Optional[str], optional): Path to the template directory. Defaults to None.
        """
        if template_dir is None:
            template_dir = Path(__file__).parent.parent / "templates"
        
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        
        # Register custom filters
        self._register_filters()
        
        # Register custom tests
        self._register_tests()
        
        # Register custom global functions
        self._register_globals()
    
    def _register_filters(self) -> None:
        """Register custom Jinja2 filters."""
        # Date and time formatting
        self.env.filters["vintage_date"] = self.vintage_date_format
        self.env.filters["vintage_time"] = self.vintage_time_format
        self.env.filters["dateline"] = self.create_dateline
        
        # Text formatting
        self.env.filters["format_headline"] = self.format_headline
        self.env.filters["format_byline"] = self.format_byline
        self.env.filters["format_title"] = self.format_title
        self.env.filters["format_lead"] = self.format_lead_paragraph
        self.env.filters["small_caps"] = self.small_caps
        
        # Layout helpers
        self.env.filters["column_split"] = self.split_into_columns
        self.env.filters["word_count"] = self.word_count
        
        # Citation helpers
        self.env.filters["format_citation"] = self.format_citation
        self.env.filters["citation_list"] = self.format_citation_list
    
    def _register_tests(self) -> None:
        """Register custom Jinja2 tests."""
        self.env.tests["feature_article"] = self.is_feature_article
        self.env.tests["has_image"] = self.has_image
        self.env.tests["long_article"] = self.is_long_article
    
    def _register_globals(self) -> None:
        """Register custom Jinja2 global functions."""
        self.env.globals["format_quote"] = self.format_pull_quote
        self.env.globals["generate_toc"] = self.generate_table_of_contents
        self.env.globals["render_figure"] = self.render_figure
        self.env.globals["current_year"] = datetime.now().year
    
    def get_template(self, template_name: str) -> Template:
        """Get a template by name.

        Args:
            template_name (str): Template name

        Returns:
            Template: Jinja2 template
        """
        return self.env.get_template(template_name)
    
    def render_template(self, template_name: str, **context: Any) -> str:
        """Render a template with the given context.

        Args:
            template_name (str): Template name
            **context: Template context

        Returns:
            str: Rendered template
        """
        template = self.get_template(template_name)
        return template.render(**context)
    
    def render_article(
        self,
        article: Article,
        template_name: str = "newspaper/article.html",
        style_guide: Optional[Dict[str, Any]] = None,
        citations: Optional[List[Citation]] = None,
        newspaper_name: str = "The FoglioAI Gazette",
        use_external_css: bool = False,
        css_path: Optional[str] = None,
    ) -> str:
        """Render an article using the specified template.

        Args:
            article (Article): Article to render
            template_name (str, optional): Template name. Defaults to "newspaper/article.html".
            style_guide (Optional[Dict[str, Any]], optional): Style guide. Defaults to None.
            citations (Optional[List[Citation]], optional): Citations. Defaults to None.
            newspaper_name (str, optional): Newspaper name. Defaults to "The FoglioAI Gazette".
            use_external_css (bool, optional): Whether to use external CSS. Defaults to False.
            css_path (Optional[str], optional): CSS path. Defaults to None.

        Returns:
            str: Rendered article
        """
        try:
            # Convert markdown content to HTML
            article_html = convert_to_html(article.content, citations, style_guide)
            
            # Prepare article metadata
            metadata = self.generate_article_metadata(article, newspaper_name)
            
            # Render the template
            return self.render_template(
                template_name,
                article=article,
                article_html=article_html,
                metadata=metadata,
                newspaper_name=newspaper_name,
                use_external_css=use_external_css,
                css_path=css_path,
            )
        except Exception as e:
            logger.error("Failed to render article template: %s", e)
            raise
    
    # Date formatting helpers
    
    def vintage_date_format(self, date: Union[datetime, str]) -> str:
        """Format a date in vintage newspaper style.

        Args:
            date (Union[datetime, str]): Date to format

        Returns:
            str: Formatted date string (e.g., "October 24, 1929")
        """
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date)
            except ValueError:
                return date
        
        return date.strftime("%B %d, %Y")
    
    def vintage_time_format(self, date: Union[datetime, str]) -> str:
        """Format a time in vintage newspaper style.

        Args:
            date (Union[datetime, str]): Date to format

        Returns:
            str: Formatted time string (e.g., "3:45 o'clock P.M.")
        """
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date)
            except ValueError:
                return date
        
        hour = date.hour
        minute = date.minute
        am_pm = "A.M." if hour < 12 else "P.M."
        
        if hour > 12:
            hour -= 12
        elif hour == 0:
            hour = 12
        
        return f"{hour}:{minute:02d} o'clock {am_pm}"
    
    def create_dateline(self, location: str, date: Optional[datetime] = None) -> str:
        """Create a vintage newspaper dateline.

        Args:
            location (str): Location name
            date (Optional[datetime], optional): Date. Defaults to None.

        Returns:
            str: Formatted dateline (e.g., "NEW YORK, Oct. 24 —")
        """
        if date is None:
            date = datetime.now()
        
        location = location.upper()
        month_abbr = date.strftime("%b").upper()
        day = date.day
        
        return f"{location}, {month_abbr}. {day} —"
    
    # Text formatting helpers
    
    def format_headline(self, text: str) -> str:
        """Format headline text in vintage newspaper style.

        Args:
            text (str): Headline text

        Returns:
            str: Formatted headline text (all caps)
        """
        # Capitalize all words
        return text.upper()
    
    def format_byline(self, byline: str) -> str:
        """Format byline in vintage newspaper style.

        Args:
            byline (str): Author byline

        Returns:
            str: Formatted byline (e.g., "By John Smith")
        """
        if not byline:
            return ""
        
        if not byline.lower().startswith("by "):
            byline = f"By {byline}"
        
        return byline
    
    def format_title(self, title: str, capitalize_all: bool = False) -> str:
        """Format article title with proper capitalization.

        Args:
            title (str): Article title
            capitalize_all (bool, optional): Whether to capitalize all words. Defaults to False.

        Returns:
            str: Formatted title
        """
        # Articles, conjunctions, and prepositions to keep lowercase
        lowercase_words = {
            "a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet",
            "at", "by", "for", "from", "in", "into", "of", "off", "on", "onto",
            "to", "upon", "with"
        }
        
        words = title.split()
        if not words:
            return ""
        
        # Always capitalize first and last word
        result = []
        for i, word in enumerate(words):
            if (capitalize_all or i == 0 or i == len(words) - 1 or 
                    word.lower() not in lowercase_words):
                result.append(word.capitalize())
            else:
                result.append(word.lower())
        
        return " ".join(result)
    
    def format_lead_paragraph(self, text: str) -> str:
        """Format the lead paragraph of an article.

        Args:
            text (str): Lead paragraph text

        Returns:
            str: Formatted lead paragraph with small caps for first few words
        """
        words = text.split()
        if len(words) <= 4:
            return f'<span class="small-caps">{text}</span>'
        
        small_caps_text = " ".join(words[:4])
        remaining_text = " ".join(words[4:])
        
        return f'<span class="small-caps">{small_caps_text}</span> {remaining_text}'
    
    def small_caps(self, text: str) -> str:
        """Convert text to small caps HTML.

        Args:
            text (str): Text to convert

        Returns:
            str: HTML with small caps styling
        """
        return f'<span class="small-caps">{text}</span>'
    
    # Layout helpers
    
    def split_into_columns(self, html: str, num_columns: int = 2) -> List[str]:
        """Split HTML content into balanced columns.

        Args:
            html (str): HTML content
            num_columns (int, optional): Number of columns. Defaults to 2.

        Returns:
            List[str]: List of HTML strings, one per column
        """
        if num_columns <= 1:
            return [html]
        
        # Extract paragraphs
        paragraphs = re.findall(r'<p[^>]*>.*?</p>', html, re.DOTALL)
        if not paragraphs:
            return [html]
        
        # Distribute paragraphs across columns
        paragraphs_per_column = max(1, len(paragraphs) // num_columns)
        columns = []
        
        for i in range(0, len(paragraphs), paragraphs_per_column):
            column_paragraphs = paragraphs[i:i + paragraphs_per_column]
            columns.append("".join(column_paragraphs))
            
            # If we have enough columns, stop
            if len(columns) >= num_columns:
                # Add any remaining paragraphs to the last column
                if i + paragraphs_per_column < len(paragraphs):
                    columns[-1] += "".join(paragraphs[i + paragraphs_per_column:])
                break
        
        return columns
    
    def word_count(self, text: str) -> int:
        """Count words in a text string.

        Args:
            text (str): Text to count

        Returns:
            int: Word count
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]*>', '', text)
        
        # Count words
        return len(re.findall(r'\b\w+\b', text))
    
    # Citation helpers
    
    def format_citation(self, citation: Citation) -> str:
        """Format a citation in vintage newspaper style.

        Args:
            citation (Citation): Citation object

        Returns:
            str: Formatted citation HTML
        """
        date_str = self.vintage_date_format(citation.published_at) if citation.published_at else ""
        
        return Markup(
            f'<div class="citation">'
            f'<cite class="citation-title">'
            f'<a href="{citation.url}" target="_blank" rel="noopener">{citation.title}</a>'
            f'</cite>'
            f'<div class="citation-metadata">'
            f'<span class="citation-date">{date_str}</span>'
            f'</div>'
            f'<blockquote class="citation-excerpt">{citation.excerpt}</blockquote>'
            f'</div>'
        )
    
    def format_citation_list(self, citations: List[Citation]) -> str:
        """Format a list of citations in vintage newspaper style.

        Args:
            citations (List[Citation]): List of citations

        Returns:
            str: Formatted citation list HTML
        """
        if not citations:
            return ""
        
        citation_html = [
            '<div class="citations">',
            '<h2 class="citations-heading">Sources</h2>',
            '<div class="citation-list">',
        ]
        
        for citation in citations:
            citation_html.append(str(self.format_citation(citation)))
        
        citation_html.extend(['</div>', '</div>'])
        
        return Markup("\n".join(citation_html))
    
    # Template testing helpers
    
    def is_feature_article(self, article: Article) -> bool:
        """Check if an article is a feature article.

        Args:
            article (Article): Article to check

        Returns:
            bool: True if feature article, False otherwise
        """
        # Feature articles typically have longer content and a subtitle
        return bool(article.subtitle) and self.word_count(article.content) > 500
    
    def has_image(self, article: Article) -> bool:
        """Check if an article has images.

        Args:
            article (Article): Article to check

        Returns:
            bool: True if article has images, False otherwise
        """
        return "![" in article.content
    
    def is_long_article(self, article: Article) -> bool:
        """Check if an article is long.

        Args:
            article (Article): Article to check

        Returns:
            bool: True if long article, False otherwise
        """
        return self.word_count(article.content) > 1000
    
    # Special formatting helpers
    
    def format_pull_quote(self, quote: str, attribution: Optional[str] = None) -> str:
        """Format a pull quote in vintage newspaper style.

        Args:
            quote (str): Quote text
            attribution (Optional[str], optional): Attribution. Defaults to None.

        Returns:
            str: Formatted pull quote HTML
        """
        attribution_html = f'<cite class="pullquote-attribution">— {attribution}</cite>' if attribution else ""
        
        return Markup(
            f'<blockquote class="pullquote">'
            f'<div class="pullquote-text">{quote}</div>'
            f'{attribution_html}'
            f'</blockquote>'
        )
    
    def generate_table_of_contents(self, html: str) -> str:
        """Generate a table of contents from HTML headers.

        Args:
            html (str): HTML content

        Returns:
            str: Table of contents HTML
        """
        # Extract headers (h2 and h3)
        h2_pattern = r'<h2[^>]*>(.*?)</h2>'
        h3_pattern = r'<h3[^>]*>(.*?)</h3>'
        
        h2_matches = re.findall(h2_pattern, html, re.DOTALL)
        h3_matches = re.findall(h3_pattern, html, re.DOTALL)
        
        if not h2_matches and not h3_matches:
            return ""
        
        toc_html = ['<div class="table-of-contents">', '<h3>In This Edition</h3>', '<ul>']
        
        # Process h2 headers
        for h2 in h2_matches:
            # Clean header text (remove tags)
            clean_h2 = re.sub(r'<[^>]*>', '', h2)
            # Create anchor from heading
            anchor = clean_h2.lower().replace(' ', '-')
            toc_html.append(f'<li><a href="#{anchor}">{clean_h2}</a></li>')
        
        # Process h3 headers
        if h3_matches:
            toc_html.append('<li class="toc-subheadings"><ul>')
            for h3 in h3_matches:
                # Clean header text (remove tags)
                clean_h3 = re.sub(r'<[^>]*>', '', h3)
                # Create anchor from heading
                anchor = clean_h3.lower().replace(' ', '-')
                toc_html.append(f'<li><a href="#{anchor}">{clean_h3}</a></li>')
            toc_html.append('</ul></li>')
        
        toc_html.extend(['</ul>', '</div>'])
        
        return Markup("\n".join(toc_html))
    
    def render_figure(
        self,
        image_url: str,
        caption: Optional[str] = None,
        alt_text: Optional[str] = None,
        width: Optional[str] = None,
        height: Optional[str] = None,
        css_class: str = "article-figure",
    ) -> str:
        """Render an image figure with caption.

        Args:
            image_url (str): Image URL
            caption (Optional[str], optional): Figure caption. Defaults to None.
            alt_text (Optional[str], optional): Alt text. Defaults to None.
            width (Optional[str], optional): Image width. Defaults to None.
            height (Optional[str], optional): Image height. Defaults to None.
            css_class (str, optional): CSS class. Defaults to "article-figure".

        Returns:
            str: Figure HTML
        """
        if alt_text is None:
            alt_text = caption or "Article image"
        
        img_attrs = [f'src="{image_url}"', f'alt="{alt_text}"']
        
        if width:
            img_attrs.append(f'width="{width}"')
        if height:
            img_attrs.append(f'height="{height}"')
        
        img_html = f'<img {" ".join(img_attrs)}>'
        caption_html = f'<figcaption>{caption}</figcaption>' if caption else ""
        
        return Markup(
            f'<figure class="{css_class}">'
            f'{img_html}'
            f'{caption_html}'
            f'</figure>'
        )
    
    def generate_article_metadata(
        self,
        article: Article,
        newspaper_name: str = "The FoglioAI Gazette",
    ) -> Dict[str, str]:
        """Generate metadata for an article.

        Args:
            article (Article): Article
            newspaper_name (str, optional): Newspaper name. Defaults to "The FoglioAI Gazette".

        Returns:
            Dict[str, str]: Article metadata
        """
        metadata = {
            "title": f"{article.title} | {newspaper_name}",
            "description": article.subtitle or (article.content[:150] + "..." if len(article.content) > 150 else article.content),
            "author": article.author or "FoglioAI Correspondent",
            "date": self.vintage_date_format(article.created_at or datetime.now()),
        }
        
        return metadata


# Global template manager instance
template_manager = TemplateManager() 