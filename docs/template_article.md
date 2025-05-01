# Article Template Documentation (`article.html`)

This document describes the structure and features of the FoglioAI article template, which extends the base template to render vintage-style articles.

---

## Overview
- `article.html` extends `base.html` and provides a two-column, print-inspired layout for articles.
- It uses Jinja2 blocks and custom CSS for advanced typography, drop caps, blockquotes, figures, and citations.

---

## Block Usage
- **`{% extends "base.html" %}`**: Inherits all base layout and styles.
- **`{% block title %}`**: Sets the page title to the article's title.
- **`{% block head %}`**: Adds article-specific CSS for layout, typography, and print.
- **`{% block content %}`**: Main article markup, including header, content, and citations.
- **`{% block footer %}`**: Custom footer with article date.

---

## Article Layout
- **Header**: Centered date, title, and optional subtitle.
- **Content**: Rendered in `.article-content` with two columns (one on mobile/print).
- **Footer**: Shows generation date.

---

## Article Content Features
- **Dropcap**: Large first letter for vintage effect (`.dropcap`).
- **Lead-in**: Bold intro paragraph (`.lead-in`).
- **Blockquotes**: Indented, italic, with accent border.
- **Figures**: Full-width images with captions.
- **Tables**: Styled for readability.

**Example content block:**
```html
<div class="article-content">
  <p><span class="dropcap">T</span>his is the first paragraph...</p>
  <blockquote>"A period quote."</blockquote>
  <figure>
    <img src="machine.jpg" alt="Early Computing Machine">
    <figcaption>Early Computing Machine</figcaption>
  </figure>
</div>
```

---

## Citations
- If `article.sources` is present, a Sources section is rendered at the end.
- Each citation includes:
  - Title (linked)
  - Publication date
  - Optional excerpt (as blockquote)

**Example citation block:**
```html
<section class="citations">
  <h2>Sources</h2>
  <ul class="citation-list">
    <li class="citation">
      <a href="https://example.com">Example Source</a>
      <span class="citation-date">March 15, 1925</span>
      <blockquote class="citation-excerpt">Excerpt from the source...</blockquote>
    </li>
  </ul>
</section>
```

---

## Responsive & Print Styles
- **Responsive**: One column on mobile, smaller headings, dropcap shrinks.
- **Print**: Two columns, larger headings, page-break rules for blockquotes/figures, sources start on new page.

---

## Example Data
**Jinja context for rendering:**
```python
article = {
  "title": "The Rise of Artificial Intelligence",
  "subtitle": "A Modern Marvel in the Making",
  "created_at": datetime(1925, 3, 15),
  "content": "<p><span class='dropcap'>I</span>n a remarkable development...</p>",
  "sources": [
    {
      "url": "https://example.com/ai-history",
      "title": "The History of AI",
      "published_at": datetime(1924, 1, 1),
      "excerpt": "Early developments in artificial intelligence..."
    }
  ]
}
```

---

## Extension Tips
- Use semantic HTML for accessibility.
- Add custom classes for new content types (e.g., sidebars, timelines).
- Override or extend styles in the `head` block as needed. 