"""Markdown to HTML conversion utilities."""
import re
from typing import Dict, List, Optional

import markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.treeprocessors import Treeprocessor

from app.models.article import Article
from app.models.article_run import Citation


class DatelinePattern(InlineProcessor):
    """Custom pattern for dateline formatting."""

    def handleMatch(self, m, data):
        """Handle dateline match."""
        dateline = m.group(1)
        el = markdown.util.etree.Element("div")
        el.set("class", "dateline")
        el.text = dateline
        return el, m.start(0), m.end(0)


class LeadInPattern(InlineProcessor):
    """Custom pattern for lead-in paragraph formatting."""

    def handleMatch(self, m, data):
        """Handle lead-in match."""
        text = m.group(1)
        el = markdown.util.etree.Element("p")
        el.set("class", "lead-in")
        el.text = text
        return el, m.start(0), m.end(0)


class DropCapProcessor(Treeprocessor):
    """Add drop caps to first letter of first paragraph."""

    def run(self, root):
        """Process the first paragraph."""
        for elem in root.iter("p"):
            if elem.text and not elem.get("class"):
                first_letter = elem.text[0]
                rest = elem.text[1:]
                elem.text = ""

                span1 = markdown.util.etree.SubElement(elem, "span")
                span1.set("class", "dropcap")
                span1.text = first_letter

                span2 = markdown.util.etree.SubElement(elem, "span")
                span2.text = rest

                # Only process first paragraph
                break


class NewspaperStyleExtension(Extension):
    """Custom markdown extension for vintage newspaper styling."""

    def extendMarkdown(self, md: markdown.Markdown) -> None:
        """Add custom processors to the markdown parser.

        Args:
            md (markdown.Markdown): Markdown parser instance
        """
        # Add custom inline patterns
        md.inlinePatterns.register(
            DatelinePattern(r"\[dateline\](.*?)\[/dateline\]"), "dateline", 175
        )
        md.inlinePatterns.register(
            LeadInPattern(r"\[lead\](.*?)\[/lead\]"), "lead-in", 176
        )

        # Add custom processors
        md.treeprocessors.register(DropCapProcessor(md), "dropcap", 15)


def render_citations(citations: List[Citation]) -> str:
    """Render citations as HTML.

    Args:
        citations (List[Citation]): List of citations to render

    Returns:
        str: HTML string of rendered citations
    """
    if not citations:
        return ""

    html = ['<div class="citations">']
    html.append('<h2>Sources</h2>')
    html.append('<ul class="citation-list">')

    for citation in citations:
        html.append(
            f'<li class="citation">'
            f'<a href="{citation.url}" target="_blank">'
            f'{citation.title}</a>'
            f'<span class="citation-date">{citation.published_at:%B %d, %Y}</span>'
            f'<blockquote class="citation-excerpt">{citation.excerpt}</blockquote>'
            f"</li>"
        )

    html.append("</ul>")
    html.append("</div>")
    return "\n".join(html)


def process_images(content: str) -> str:
    """Process image markdown to add captions and styling.

    Args:
        content (str): Markdown content with images

    Returns:
        str: Processed markdown with styled images
    """
    # Replace standard markdown images with custom figure/figcaption
    pattern = r"!\[(.*?)\]\((.*?)\)"
    replacement = r'<figure class="article-figure">\n<img src="\2" alt="\1">\n<figcaption>\1</figcaption>\n</figure>'
    return re.sub(pattern, replacement, content)


def apply_typography(html: str) -> str:
    """Apply typographic enhancements to HTML.

    Args:
        html (str): Raw HTML content

    Returns:
        str: HTML with typographic enhancements
    """
    # Smart quotes
    html = re.sub(r'"([^"]*)"', r'"\1"', html)
    html = re.sub(r"'([^']*)'", r"'\1'", html)

    # Em dashes
    html = re.sub(r"\s*--\s*", "—", html)

    # Ellipsis
    html = re.sub(r"\.\.\.", "…", html)

    # Clean up whitespace
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r"\s*\n\s*", "\n", html)

    return html.strip()


def convert_to_html(
    content: str,
    citations: Optional[List[Citation]] = None,
    style_guide: Optional[Dict[str, str]] = None,
) -> str:
    """Convert markdown content to styled HTML.

    Args:
        content (str): Markdown content to convert
        citations (Optional[List[Citation]], optional): List of citations. Defaults to None.
        style_guide (Optional[Dict[str, str]], optional): Style guide options. Defaults to None.

    Returns:
        str: HTML content with vintage newspaper styling
    """
    # Process images first
    content = process_images(content)

    # Configure Markdown
    md = markdown.Markdown(
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.attr_list",
            "markdown.extensions.def_list",
            "markdown.extensions.footnotes",
            "markdown.extensions.abbr",
            "markdown.extensions.admonition",
            "markdown.extensions.meta",
            "markdown.extensions.sane_lists",
            "markdown.extensions.smarty",
            "markdown.extensions.toc",
            NewspaperStyleExtension(),
        ]
    )

    # Convert markdown to HTML
    html = md.convert(content)

    # Apply typography enhancements
    html = apply_typography(html)

    # Add citations if provided
    if citations:
        html += "\n" + render_citations(citations)

    return html 