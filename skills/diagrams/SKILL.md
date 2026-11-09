---
name: diagrams
description: >
  Default skill for creating or revising diagrams, flow charts, schematics,
  process flows, architecture drawings, network topologies, dependency graphs,
  or concept maps that represent conceptual relationships. Uses TikZ flowcharts
  by default unless the user explicitly requests another diagram format such as
  Mermaid or Graphviz. Applies to static and interactive diagrams, rather than
  data plots.
---

# Diagrams (TikZ Flowchart Default)

Make the entities, relationships, direction, and scope explicit before choosing
the layout. A network showing conceptual dependencies belongs here; a network
encoding measured quantities may also need data visualization guidance.

Read [visual design](../data-visualization/references/visual-design.md).
Use `waterology config context diagrams` for optional local guidance, or the
[local resolver](../project-conventions/references/local-preferences.md).

Use TikZ by default whenever creating or updating flowcharts, system
architectures, pipelines, or technical diagrams unless the user explicitly asks
for another format (such as a "mermaid diagram" or "graphviz") or you are
extending an existing editable SVG or Mermaid diagram source.

## 1. Core Conventions

1. **Fenced TikZ Blocks with Captions**:
   - In Markdown documentation, write diagrams inside ```` ```tikz ```` fenced code blocks.
   - Always begin each block with a `% caption: ...` comment describing the figure:
     ```tikz
     % caption: Three-stage compilation, optimization, and verification pipeline.
     \begin{tikzpicture}[node distance=1.3cm and 2.4cm]
       ...
     \end{tikzpicture}
     ```
   - For Markdown delivery, use
     [Markdown delivery](../writing-style/references/markdown-artifacts.md). Save
     the editable TikZ source alongside the rendered SVG or required export when
     the target Markdown renderer does not compile ```` ```tikz ```` blocks directly.
2. **Sequential Figure Numbering**:
   - Number all figures (`Figure 1`, `Figure 2`, ...) sequentially in reading order across the documentation, wrapping both TikZ diagrams (`.tikz-figure`) and plot images (`.plot-figure`) in:
     ```html
     <figure class="guide-figure tikz-figure" id="fig-N">
       <div class="tikz-container"><div class="tikz-svg">...</div></div>
       <figcaption><strong>Figure N:</strong> Caption text...</figcaption>
     </figure>
     ```
3. **Earth-Tone 7-Role Palette and Automatic Legend**:
   - Use the reusable style package [`resources/flowchart-tikz.sty`](./resources/flowchart-tikz.sty), which provides 7 distinct shapes and earth-tone color roles, automatic Light/Dark mode CSS custom property mapping (`--m-*`), and an automatic compact legend bar at the bottom of every diagram showing only the styles used in that diagram (disable with `\begin{tikzpicture}[no legend]` when not needed).
   - Label nodes and meaningful edges. Distinguish sequence, dependency, data movement, and feedback rather than using the same arrow for every relationship. Split an unreadable overview into a small overview and focused details.

| Semantic Role | Shape Style | Rectangular Variant | Typical Use |
| :--- | :--- | :--- | :--- |
| **1. Data / Storage / State** | `store` (alias `data`, `obs`, `res`) | `storebox` | Databases, state stores, observed data, buffers |
| **2. Process / Transform / Channel** | `proc` (alias `transform`, `proxy`, `reach`) | `procbox` | Transforms, conveyors, channels, operators |
| **3. Junction / Merge / Output** | `junc` (alias `merge`, `prod`) | `juncbox` | Aggregators, confluences, verified outputs |
| **4. Rule / Policy / Model** | `rule` (alias `policy`, `latent`) | `rulebox` | Controllers, policies, rules, core algorithms |
| **5. Condition / Gate / Guard** | `cond` (alias `gate`, `cut`) | `condbox` | Branch conditions, thresholds, validation gates |
| **6. Stage / Module / Tool** | `stage` (alias `module`, `equip`) | `stagebox` | Pipeline stages, solvers, hardware/software modules |
| **7. I/O / Boundary / Artifact** | `io` (alias `artifact`) | `iobox` | Exogenous inputs, CLI commands, files, artifacts |

---

## 2. Strict Layout and Geometry Rules

Every TikZ diagram **must** obey four geometric invariants so arrows never tilt diagonally by accident, rounded corners never clip or reverse, and labels never collide:

### Rule A: Strict Vertical Alignment (`dx = 0`) in Vertical Flowcharts
- `below=... of nodeA` aligns horizontal centers (`x`), whereas `below right=` or chaining left-to-right across rows of varying text widths shifts horizontal centers.
- **Multi-column rows inside `group` containers**:
  1. Give cards in a grid a uniform width (`card/.style={text width=4.6cm, align=center}`).
  2. Place the **center column node first** (`below=... of prev_center`), then place left and right column nodes relative to the center node (`left=1.2cm of center_node`, `right=1.2cm of center_node`). This guarantees every row and every fitted `group` container is centered at `x = 0`.
  3. When drawing vertical arrows between `group` containers whose internal nodes have mixed shapes, anchor the vertical arrow to the center column's X coordinate:
     ```latex
     \draw[flow] (center_top.center |- Group1.south) -- (center_bot.center |- Group2.north);
     ```

### Rule B: Strict Horizontal Alignment (`dy = 0`) in Horizontal Flowcharts
- Place horizontal peers relative to each other (`right=2.4cm of peer`) so their vertical centers (`y`) match (`dy = 0`).
- **Fan-out / fan-in columns**:
  - Place the middle node of the target column directly `right=2.8cm of source_node` (or for an even number of nodes, place the top node `right=2.8cm of source_node, yshift=1.1cm` and the bottom node `below=... of top_node` so both share the exact same center X).
  - Give all nodes in a vertically stacked column a **uniform `text width`** (`scard/.style={text width=5.5cm, align=center}`) so their `.west`, `.center`, and `.east` anchors are all vertically aligned.
- **Parallel subgraphs**:
  - Use identical internal vertical spacing (`below=1.1cm of ...`) inside side-by-side `group` containers, or connect them using explicit horizontal projection:
    ```latex
    \draw[flow] ([yshift=0.6cm]GroupA.east) -- ([yshift=0.6cm]GroupA.east -| GroupB.west);
    ```

### Rule C: Generous Clearance for Rounded-Corner Turns (`rounded corners=4pt`)
- Connectors (`flow`, `sig`, `bidir`) use `rounded corners=4pt` (`C` Bezier curves in SVG) and `>=Latex` arrowheads (`~7.5pt` long).
- If any straight leg adjacent to an orthogonal turn (`-|` or `|-`) is shorter than `~12pt` before arrowhead shortening (`< 7.5pt` visible shaft), the `4pt` rounded corner overshoots the arrowhead base and reverses direction or looks cramped.
- **Minimum spacing**:
  - Leave at least **`1.5cm-1.8cm`** vertical gap between rows connected by an L-turn or Z-turn (`-- ++(0,-0.7cm) -|`).
  - Leave at least **`0.75cm-0.95cm`** (`21-27pt`) on the horizontal or vertical drop leg before/after every turn:
    ```latex
    \coordinate (turn_x) at ([xshift=-0.85cm]target.west);
    \draw[flow] (src.east) -- (src.east -| turn_x) |- (target.west);
    ```

### Rule D: Non-Overlapping Edge Labels (`elabel`)
- Never place `node[elabel]` at the default midpoint of an L-shaped path (`|-` or `-|`), which lands directly on the corner bend. Always specify `pos=0.25` (first leg) or `pos=0.75` (second leg).
- Give labeled straight connectors at least `2.8cm-3.8cm` separation between nodes so the `elabel` pill clears both endpoints by `>= 1.5pt`.

---

## 3. Verification Workflow

Render and inspect the chosen layout. Confirm that arrows connect the right
entities and the diagram agrees with the supplied process or implementation.
Always verify compiled TikZ SVGs using [`scripts/check_tikz_svg.py`](./scripts/check_tikz_svg.py)
(resolved relative to this skill directory):

```sh
python3 <skill-directory>/scripts/check_tikz_svg.py path/to/file.md
```

The verifier compiles ```` ```tikz ```` blocks (or inspects existing `.svg`/`.html` files) and fails with exact coordinates if any diagram has:
1. Node-node bounding-box overlap (`pad = 4.0pt`)
2. Edge-label-node overlap (`pad = 1.5pt`)
3. Edge-label-edge-label overlap (`pad = 2.0pt`)
4. Connector segment crossing or grazing a non-endpoint node (`pad = 1.5pt`) or penetrating an endpoint node (`pad = -3.0pt`)
5. Unintended diagonal connector segments (`abs(dx) > 0.3 && abs(dy) > 0.3`)
6. Reversed or cramped straight legs (`< 7.5pt`) before or after a rounded corner (`C`).

For integrating TikZ compilation, CSS theme variables, and sequential figure numbering into a Python or Julia documentation build script, see [`references/integration-patterns.md`](./references/integration-patterns.md).

Only for requested interaction, load
[interactive-graphics](../interactive-graphics/SKILL.md). A TikZ SVG or Mermaid
block in an HTML page is not, by itself, an interactive diagram.
