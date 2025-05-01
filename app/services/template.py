"""Template rendering service."""
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.article import Article
from app.utils.markdown import convert_to_html

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """Template renderer service."""

    def __init__(self) -> None:
        """Initialize the template renderer."""
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render_article(
        self,
        article: Article,
        style_guide: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render an article using the article template.

        Args:
            article (Article): Article to render
            style_guide (Optional[Dict[str, Any]], optional): Style guidelines. Defaults to None.

        Returns:
            str: Rendered HTML
        """
        try:
            # Convert markdown content to HTML
            article_html = convert_to_html(article.content, style_guide)

            # Get the template
            template = self.env.get_template("article.html")

            # Render the template
            return template.render(
                article=article,
                article_html=article_html,
            )
        except Exception as e:
            logger.error("Failed to render article template: %s", e)
            raise


# Global template renderer instance
template_renderer = TemplateRenderer() 