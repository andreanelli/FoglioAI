# Template Example Gallery

This gallery showcases common layouts, typography, and component variations for the FoglioAI vintage newspaper theme.

---

## Common Layouts

### 1. Standard Article
```html
<article>
  <header class="article-header">
    <div class="article-date">March 15, 1925</div>
    <h1 class="article-title">The Rise of Artificial Intelligence</h1>
    <div class="article-subtitle">A Modern Marvel in the Making</div>
  </header>
  <div class="article-content">
    <p><span class="dropcap">I</span>n a remarkable development...</p>
    <!-- ... -->
  </div>
</article>
```

### 2. Article with Sidebar
```html
<main>
  <article>...</article>
  <aside class="sidebar">
    <h3>Related Articles</h3>
    <ul>
      <li><a href="#">The History of AI</a></li>
    </ul>
  </aside>
</main>
```

---

## Typography Examples

### Headings
```html
<h1 class="article-title">Main Headline</h1>
<h2>Section Heading</h2>
```

### Paragraphs & Lead-in
```html
<p class="lead-in">In a remarkable development...</p>
<p>Scientists and engineers...</p>
```

### Blockquote
```html
<blockquote>"We stand at the threshold of a new era."</blockquote>
```

---

## Component Variations

### Figure with Caption
```html
<figure>
  <img src="machine.jpg" alt="Early Computing Machine">
  <figcaption>Early Computing Machine</figcaption>
</figure>
```

### Table
```html
<table>
  <tr><th>Year</th><th>Event</th></tr>
  <tr><td>1925</td><td>AI Breakthrough</td></tr>
</table>
```

### Citations Section
```html
<section class="citations">
  <h2>Sources</h2>
  <ul class="citation-list">
    <li class="citation">
      <a href="#">Example Source</a>
      <span class="citation-date">March 15, 1925</span>
      <blockquote class="citation-excerpt">Excerpt from the source...</blockquote>
    </li>
  </ul>
</section>
```

---

## Responsive Demos

- **Desktop:** Two-column article content, large headings, horizontal nav.
- **Mobile:** Single-column content, smaller headings, vertical nav.

<!--
Add screenshots or diagrams here for visual reference.
E.g.:
![Desktop Layout](screenshots/desktop_layout.png)
![Mobile Layout](screenshots/mobile_layout.png)
--> 