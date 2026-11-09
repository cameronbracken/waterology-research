# Integrating TikZ Diagrams and Sequential Figure Numbering in Documentation Builders

## 1. Light and Dark Theme CSS Custom Variables

Include these CSS custom properties in your documentation stylesheet so inline SVGs compiled with `\def\FLOWCHARTWEB{1}` automatically adapt to Light and Dark themes:

```css
:root {
  /* Earth-Tone Light Theme Diagram Palette */
  --m-bg: #faf9f6;
  --m-cluster-bg: #f4f1ea;
  --m-cluster-border: #b8b0a4;
  --m-cluster-text: #4a453e;
  --m-line: #575148;
  --m-edge-bg: #faf8f5;
  --m-edge-border: #cec7bc;
  --m-edge-text: #38342e;
  --m-res-fill: #dbe7ee;   --m-res-stroke: #2b5b7c;   --m-res-text: #162e40;
  --m-reach-fill: #dcebe5; --m-reach-stroke: #2d6a58; --m-reach-text: #15352b;
  --m-junc-fill: #e3ead9;  --m-junc-stroke: #4d6b31;  --m-junc-text: #223314;
  --m-rule-fill: #efe3dc;  --m-rule-stroke: #8c4a32;  --m-rule-text: #3d1d11;
  --m-cond-fill: #f5ead4;  --m-cond-stroke: #9c6b1b;  --m-cond-text: #3d2806;
  --m-equip-fill: #e8e0ea; --m-equip-stroke: #6b4c75; --m-equip-text: #2d1d33;
  --m-io-fill: #efece6;    --m-io-stroke: #686259;    --m-io-text: #26231f;
}

[data-theme="dark"] {
  /* Earth-Tone Dark Theme Diagram Palette */
  --m-bg: #141a24;
  --m-cluster-bg: #1b222e;
  --m-cluster-border: #5c564e;
  --m-cluster-text: #d6cfc5;
  --m-line: #a8a095;
  --m-edge-bg: #1e242d;
  --m-edge-border: #59534b;
  --m-edge-text: #e6e0d6;
  --m-res-fill: #183042;   --m-res-stroke: #6ba3c7;   --m-res-text: #e3eef5;
  --m-reach-fill: #16332b; --m-reach-stroke: #63b097; --m-reach-text: #dff2ec;
  --m-junc-fill: #233019;  --m-junc-stroke: #8cb369;  --m-junc-text: #e8f2de;
  --m-rule-fill: #382018;  --m-rule-stroke: #d48466;  --m-rule-text: #f7e6df;
  --m-cond-fill: #362810;  --m-cond-stroke: #deb059;  --m-cond-text: #faefd9;
  --m-equip-fill: #2d1f33; --m-equip-stroke: #b38ebf; --m-equip-text: #f0e6f5;
  --m-io-fill: #262421;    --m-io-stroke: #9c9488;    --m-io-text: #ebe6df;
}

.guide-figure {
  margin: 1.4rem 0;
}
.guide-figure .tikz-container {
  background: var(--m-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.85rem 1.1rem;
  margin: 0;
  overflow-x: auto;
}
.guide-figure .tikz-svg {
  text-align: center;
  padding: 0.4rem 0;
}
.guide-figure .tikz-svg svg {
  max-width: 100%;
  height: auto;
  display: inline-block;
}
.guide-figure figcaption {
  margin-top: 0.55rem;
  font-size: 0.86rem;
  color: var(--text-muted);
  text-align: center;
  line-height: 1.45;
}
.guide-figure figcaption strong {
  color: var(--text);
}
```

## 2. Sequential Figure Numbering Pattern

To number both TikZ diagrams and standalone plot images (`![alt]({{src}})`) sequentially (`Figure 1`, `Figure 2`, ...) in reading order across multi-page documentation:

1. Pre-scan the ordered chapter list (`ORDERED_PAGES`) to count ```` ```tikz ```` blocks and standalone `![alt]({{src}})` images per page, recording `page_start_fig[page]`.
2. When rendering a page:
   - Compile each ```` ```tikz ```` block via `compile_tikz_to_svg` (which strips `% caption: ...` before computing the SHA-1 cache digest and runs `check_tikz_svg_overlaps`).
   - Emit `<div class="tikz-container" data-fig-caption="..."><div class="tikz-svg">...</div></div>`.
   - Run a single top-to-bottom regex replacement matching either `<div class="tikz-container" data-fig-caption="...">...</div></div>` or `<p><img src="..." alt="..."/></p>`, incrementing `fig_counter` and wrapping each match in `<figure class="guide-figure ..." id="fig-N">...<figcaption><strong>Figure N:</strong> ...</figcaption></figure>`.
