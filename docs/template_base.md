# Base Template Documentation (`base.html`)

This document describes the structure and style system of the FoglioAI base HTML template, which provides the foundation for all article and site pages.

---

## Overview
- The `base.html` template defines the global layout, typography, color scheme, and responsive/print rules for the vintage newspaper look.
- It uses Jinja2 blocks for extensibility and includes embedded CSS for both screen and print.

---

## Block Structure
- **`{% block title %}`**: Sets the page `<title>`. Default: `FoglioAI - Vintage Newspaper`.
- **`{% block head %}`**: For additional `<head>` content (e.g., extra styles/scripts).
- **`{% block content %}`**: Main content area. Child templates should override this.
- **`{% block footer %}`**: Footer content. Default: copyright.
- **`{% block scripts %}`**: For scripts at the end of `<body>`.

**Example usage:**
```html
{% extends "base.html" %}
{% block title %}My Article Title{% endblock %}
{% block content %}
  <h1>Article</h1>
  <p>...</p>
{% endblock %}
```

---

## CSS Variables (`:root`)
- `--font-primary`: Main font (Old Standard TT, Times New Roman, serif)
- `--color-text`: Main text color (`#2c2c2c`)
- `--color-background`: Page background (`#f4f1ea`)
- `--color-accent`: Accent color (`#8b0000`)
- `--color-border`: Border color (`#d4d0c8`)
- `--max-width`: Container max width (`1200px`)
- `--column-gap`: Column gap (`2rem`)

---

## Typography
- Uses `Old Standard TT` for a vintage look (loaded from Google Fonts).
- Headings (`h1`-`h6`) use the primary font, with spacing and border for `h1`.
- Paragraphs are justified and hyphenated for print-style flow.

---

## Navigation
- Top navigation bar with Home, Articles, About links.
- Uses flex layout for horizontal nav; stacks vertically on mobile.

---

## Responsive Design
- At widths ≤ 768px:
  - Body/container padding reduced
  - Headings shrink
  - Navigation becomes vertical

---

## Print Styles
- Print media query removes nav, background, and box-shadow.
- Enlarges padding for print margins.
- Adjusts font sizes for headings and paragraphs.

---

## Extension Guidelines
- Use `{% extends "base.html" %}` in all child templates.
- Override only the blocks you need (e.g., `content`, `title`, `footer`).
- Add custom styles/scripts in the `head` or `scripts` blocks.

---

## Example: Minimal Article Template
```html
{% extends "base.html" %}
{% block title %}Vintage Article{% endblock %}
{% block content %}
  <h1>Vintage Headline</h1>
  <p>This is a sample article in vintage style.</p>
{% endblock %}
``` 