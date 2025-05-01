"""Vintage newspaper renderer service."""
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from app.models.article import Article
from app.services.template_helpers import template_manager
from app.utils.markdown import convert_to_html

logger = logging.getLogger(__name__)


class NewspaperRenderer:
    """Vintage newspaper renderer service."""

    def __init__(self) -> None:
        """Initialize the newspaper renderer."""
        # Use the global template manager instance
        self.template_manager = template_manager

    def render_article(
        self,
        article: Article,
        style_guide: Optional[Dict[str, Any]] = None,
        use_external_css: bool = False,
        css_path: Optional[str] = None,
        newspaper_name: str = "The FoglioAI Gazette",
        citations: Optional[List] = None,
    ) -> str:
        """Render an article using the vintage newspaper template.

        Args:
            article (Article): Article to render
            style_guide (Optional[Dict[str, Any]], optional): Style guidelines. Defaults to None.
            use_external_css (bool, optional): Whether to use external CSS. Defaults to False.
            css_path (Optional[str], optional): Path to the CSS file. Defaults to None.
            newspaper_name (str, optional): Name of the newspaper. Defaults to "The FoglioAI Gazette".
            citations (Optional[List], optional): List of citations. Defaults to None.

        Returns:
            str: Rendered HTML
        """
        try:
            return self.template_manager.render_article(
                article=article,
                template_name="newspaper/article.html",
                style_guide=style_guide,
                citations=citations,
                newspaper_name=newspaper_name,
                use_external_css=use_external_css,
                css_path=css_path,
            )
        except Exception as e:
            logger.error("Failed to render newspaper article template: %s", e)
            raise

    def render_front_page(
        self,
        headline_article: Optional[Dict[str, Any]] = None,
        secondary_articles: Optional[List[Dict[str, Any]]] = None,
        row_articles: Optional[List[Dict[str, Any]]] = None,
        newspaper_name: str = "The FoglioAI Gazette",
        publication_date: Optional[datetime] = None,
        use_external_css: bool = False,
        css_path: Optional[str] = None,
    ) -> str:
        """Render a newspaper front page with multiple articles.

        Args:
            headline_article (Optional[Dict[str, Any]], optional): Main headline article. Defaults to None.
            secondary_articles (Optional[List[Dict[str, Any]]], optional): Secondary articles. Defaults to None.
            row_articles (Optional[List[Dict[str, Any]]], optional): Bottom row articles. Defaults to None.
            newspaper_name (str, optional): Name of the newspaper. Defaults to "The FoglioAI Gazette".
            publication_date (Optional[datetime], optional): Publication date. Defaults to None.
            use_external_css (bool, optional): Whether to use external CSS. Defaults to False.
            css_path (Optional[str], optional): Path to the CSS file. Defaults to None.

        Returns:
            str: Rendered HTML
        """
        try:
            # Set defaults
            if secondary_articles is None:
                secondary_articles = []
            if row_articles is None:
                row_articles = []
            if publication_date is None:
                publication_date = datetime.now()

            # Render the template using the template manager
            return self.template_manager.render_template(
                "newspaper/front_page.html",
                headline_article=headline_article,
                secondary_articles=secondary_articles,
                row_articles=row_articles,
                newspaper_name=newspaper_name,
                publication_date=publication_date,
                use_external_css=use_external_css,
                css_path=css_path,
            )
        except Exception as e:
            logger.error("Failed to render newspaper front page template: %s", e)
            raise

    # For backwards compatibility, we'll keep these methods but delegate to the template manager
    def vintage_date_format(self, date: Union[datetime, str]) -> str:
        """Format a date in vintage newspaper style.

        Args:
            date (Union[datetime, str]): Date to format

        Returns:
            str: Formatted date string
        """
        return self.template_manager.vintage_date_format(date)

    def vintage_time_format(self, date: Union[datetime, str]) -> str:
        """Format a time in vintage newspaper style.

        Args:
            date (Union[datetime, str]): Date to format

        Returns:
            str: Formatted time string
        """
        return self.template_manager.vintage_time_format(date)

    def format_headline(self, text: str) -> str:
        """Format headline text in vintage newspaper style.

        Args:
            text (str): Headline text

        Returns:
            str: Formatted headline text
        """
        return self.template_manager.format_headline(text)

    def format_byline(self, byline: str) -> str:
        """Format byline in vintage newspaper style.

        Args:
            byline (str): Author byline

        Returns:
            str: Formatted byline
        """
        return self.template_manager.format_byline(byline)

    def create_dateline(self, location: str, date: Optional[datetime] = None) -> str:
        """Create a vintage newspaper dateline.

        Args:
            location (str): Location name
            date (Optional[datetime], optional): Date for dateline. Defaults to None.

        Returns:
            str: Formatted dateline
        """
        return self.template_manager.create_dateline(location, date)


# Global newspaper renderer instance
newspaper_renderer = NewspaperRenderer() 