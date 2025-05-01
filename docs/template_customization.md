# Template Customization Guide

This guide explains how to extend and customize FoglioAI's templates and styles for your own needs.

---

## Extending Templates
- Always start by extending `base.html`:
  ```html
  {% extends "base.html" %}
  {% block content %}
    <!-- Your content here -->
  {% endblock %}
  ```
- For articles, extend `article.html` to inherit all article-specific features.
- Override only the blocks you need (e.g., `content`, `title`, `footer`, `head`).

---

## Overriding Styles
- Add custom CSS in the `head` block:
  ```html
  {% block head %}
    {{ super() }}
    <style>
      :root {
        --color-accent: #004488;
      }
      .article-title { color: var(--color-accent); }
    </style>
  {% endblock %}
  ```
- You can override any CSS variable or add new classes.

---

## Adding Custom Components
- Use semantic HTML and add new blocks or sections as needed:
  ```html
  {% block content %}
    {{ super() }}
    <aside class="sidebar">
      <h3>Related Articles</h3>
      <ul>...</ul>
    </aside>
  {% endblock %}
  ```
- Style your new components in the `head` block or a linked CSS file.

---

## Print Customization
- Use the `@media print` CSS block to adjust layout, hide elements, or change font sizes for print.
- Example: Hide sidebar on print
  ```css
  @media print {
    .sidebar { display: none; }
  }
  ```

---

## Example: Adding a Sidebar
```html
{% extends "article.html" %}
{% block head %}
  {{ super() }}
  <style>
    .sidebar {
      border-left: 2px solid var(--color-border);
      padding-left: 1rem;
      margin-top: 2rem;
      color: #555;
    }
  </style>
{% endblock %}
{% block content %}
  {{ super() }}
  <aside class="sidebar">
    <h3>Related Articles</h3>
    <ul>
      <li><a href="#">The History of AI</a></li>
      <li><a href="#">Vintage Computing</a></li>
    </ul>
  </aside>
{% endblock %}
```

---

## References
- See [template_base.md](template_base.md) and [template_article.md](template_article.md) for block and style details.
- See [style_guide.md](style_guide.md) for the full design system. 