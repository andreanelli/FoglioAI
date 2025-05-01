# FoglioAI Style Guide: Vintage Newspaper Theme

This style guide documents the design system and conventions for the FoglioAI vintage newspaper look, as implemented in the base and article templates.

---

## Typography System
- **Font Family:**
  - Primary: `Old Standard TT`, fallback to `Times New Roman`, serif
  - Set via CSS variable: `--font-primary`
- **Headings:**
  - `h1`: 3rem (desktop), 2rem (mobile), uppercase, border-bottom
  - `h2`: 2rem (desktop), 1.5rem (mobile)
  - All headings use tight line-height and spacing
- **Paragraphs:**
  - Justified, hyphenated, 1rem bottom margin
- **Special Classes:**
  - `.dropcap`: Large first letter, bold, floats left
  - `.lead-in`: Bold, larger intro paragraph

---

## Color Palette
- **Text:** `#2c2c2c` (`--color-text`)
- **Background:** `#f4f1ea` (`--color-background`)
- **Accent:** `#8b0000` (`--color-accent`)
- **Border:** `#d4d0c8` (`--color-border`)
- **Citation Block:** Light gray background, accent border

---

## Spacing & Grid
- **Container:**
  - Max width: 1200px (`--max-width`)
  - Padding: 2rem (desktop), 1rem (mobile)
- **Columns:**
  - `.article-content`: 2 columns (desktop/print), 1 column (mobile)
  - Column gap: 2rem (`--column-gap`)
- **Section Spacing:**
  - Headings, nav, and citations have extra margin for separation

---

## Responsive Breakpoints
- **Mobile (≤ 768px):**
  - Container and body padding reduced
  - Headings and dropcap shrink
  - Navigation stacks vertically
  - Article content becomes single column

---

## Custom Elements & Classes
- **Navigation:** Flex layout, horizontal on desktop, vertical on mobile
- **Blockquotes:** Italic, indented, accent border, full column span
- **Figures:** Full width, caption styled italic and centered
- **Tables:** Bordered, full width, styled headers
- **Citations:** Section at end, with title, date, and excerpt

---

## Print Customization
- **Print Media Query:**
  - Removes nav and background
  - Enlarges padding for margins
  - Adjusts font sizes for headings and paragraphs
  - Ensures two-column layout for article content
  - Starts citations on a new page

---

## Example: Article Section
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

## Customization Tips
- Override CSS variables in the `head` block for color or font changes
- Add new classes for custom layouts or elements
- Use semantic HTML for accessibility and print fidelity 