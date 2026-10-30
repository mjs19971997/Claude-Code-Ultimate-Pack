# Matplotlib Figures for Papers

Reference for producing journal-ready figures with Matplotlib 3.11.2 (checked 2026-10; run on Python 3.13): sizing to column width, vector output, fonts, layout, colors and a figure-script template. Always take the final dimensions, font and file-format rules from the target journal's author guidelines.

## Contents

1. [Principles](#1-principles)
2. [Sizing to the column width](#2-sizing-to-the-column-width)
3. [rcParams and style files](#3-rcparams-and-style-files)
4. [Vector output and fonts](#4-vector-output-and-fonts)
5. [Layout](#5-layout)
6. [Color and accessibility](#6-color-and-accessibility)
7. [Dense data in vector files](#7-dense-data-in-vector-files)
8. [Figure script template](#8-figure-script-template)
9. [Checklist before submission](#9-checklist-before-submission)

## 1. Principles

- Create the figure at its final printed size and font size. Scaling a PDF in the manuscript changes the text size you chose.
- Generate every figure from a script that reads saved data; never save only a hand-tuned interactive window.
- Use vector formats (PDF, SVG, EPS) for line art and text, raster (PNG, TIFF at 300 dpi or more) for photographs and images.
- Use the object-oriented API (`fig, ax = plt.subplots(...)`) and call `fig.savefig`, not `plt.savefig`, so several figures in one process stay separate.
- Run scripts headless with `MPLBACKEND=Agg` or `matplotlib.use("Agg")` before importing `pyplot`.
- Close figures you do not reuse (`plt.close(fig)`) in loops; the default `figure.max_open_warning` is 20.

## 2. Sizing to the column width

`figsize` is in inches by default. Matplotlib 3.11.2 also accepts a unit as a third element, for example `figsize=(8.5, 6, "cm")` (checked: `fig.get_size_inches()` returns the converted values).

```python
MM = 1.0 / 25.4

single = 86 * MM        # example only: use your journal's single-column width
double = 178 * MM       # example only: use your journal's full-page width

fig, ax = plt.subplots(figsize=(single, 0.72 * single), layout="constrained")
```

- Typical journal column widths are in the range of 8.5 to 9 cm for one column and 17 to 18 cm for two; the exact numbers differ per publisher, so read the guidelines.
- Aspect ratios around 0.7 (height over width) work for single plots; use the golden ratio only if you like it, not because it is required.
- Keep text between about 6 and 9 points at final size; match the caption font size of the journal. Set `font.size`, `axes.labelsize`, `xtick.labelsize`, `ytick.labelsize` and `legend.fontsize` explicitly.
- Line widths of 0.5 to 1.5 points survive reduction; hairlines below 0.25 pt may disappear in print.
- Check the result by opening the PDF at 100 percent: the text should look like the body of the paper.

## 3. rcParams and style files

Keep settings in a style file and load it once.

```text
# styles/paper.mplstyle
font.size: 8
axes.labelsize: 8
axes.titlesize: 8
legend.fontsize: 7
xtick.labelsize: 7
ytick.labelsize: 7
axes.linewidth: 0.6
xtick.major.width: 0.6
ytick.major.width: 0.6
lines.linewidth: 1.0
legend.frameon: False
pdf.fonttype: 42
ps.fonttype: 42
savefig.bbox: tight
savefig.pad_inches: 0.02
```

- Load with `plt.style.use("styles/paper.mplstyle")` (a path) or `plt.style.use(["petroff10", "styles/paper.mplstyle"])`; later styles override earlier ones.
- Use `with plt.style.context(...)` for a temporary change inside library code so global state is not left modified.
- Defaults to know (3.11.2): `image.cmap` is `viridis`, `figure.figsize` is `[6.4, 4.8]`, `figure.dpi` is 100, `savefig.dpi` is `figure`, `pdf.fonttype` is 3, `svg.fonttype` is `path`, `figure.constrained_layout.use` is `False`.
- `savefig.bbox: tight` crops to content and can change the final size slightly; for exact column widths either leave it off and rely on `layout="constrained"`, or keep the padding small and verify the size of the output.

## 4. Vector output and fonts

- PDF: `fig.savefig("fig1.pdf")`. Set `pdf.fonttype` to 42 to embed TrueType fonts; the default of 3 (Type 3) is rejected by some publishers and is harder to edit in vector editors. The same applies to `ps.fonttype` for EPS.
- SVG: the default `svg.fonttype: path` converts text to outlines (exact look, text not selectable); `svg.fonttype: none` keeps text as text and relies on the viewer having the font.
- Font choice: the default DejaVu Sans is always available. To match a serif body font, set `font.family` to an installed font, or use mathtext with `mathtext.fontset: stix` for Times-like math without a LaTeX installation.
- `text.usetex: True` renders all text with a local LaTeX installation: the fonts match the paper exactly, but it needs LaTeX, is slower and reads `text.latex.preamble`. Keep the preamble short and do not paste untrusted strings into labels when `usetex` is on. The LaTeX side of the manuscript is covered by latex-academic-expert.
- Reproducible PDFs: `fig.savefig("fig.pdf", metadata={"CreationDate": None})` leaves out the timestamp so repeated runs give identical files.
- Rasters embedded in vector files: `savefig.dpi` applies to rasterized artists (see section 7); set `dpi=300` or higher in `savefig` for them.
- PNG for slides and web: `fig.savefig("fig.png", dpi=300)`; use `transparent=True` only when the destination background is known.

## 5. Layout

- Use the layout engines: `plt.subplots(..., layout="constrained")` (also `plt.figure(layout="constrained")`). In 3.11.2 `fig.get_layout_engine()` returns a `ConstrainedLayoutEngine`. This replaces `constrained_layout=True` and most `tight_layout()` calls; `layout="tight"` remains for simple cases.
- `fig.subplot_mosaic([["a", "b"], ["c", "c"]], layout="constrained")` builds irregular grids with named axes; `fig.subfigures` gives independent panels with their own titles.
- Panel labels: `ax.text(0.0, 1.02, "(a)", transform=ax.transAxes, fontweight="bold")` or `ax.set_title("(a)", loc="left")`.
- Share axes with `sharex=True` / `sharey=True` and hide duplicated tick labels with `ax.label_outer()`.
- Colorbars: `fig.colorbar(im, ax=ax, label="...")` steals space from `ax` under constrained layout; use `shrink` and `pad` sparingly, and `location="right"` or `"top"` for placement.
- Align labels across panels with `fig.align_labels()`.
- Axis labels carry units: `"Time (s)"`, `"Energy (eV)"`; use `ax.set(xlabel=..., ylabel=...)` for brevity.
- Legends: `frameon=False`, placed inside the axes where empty (`loc="best"` is a guess; prefer an explicit location) or outside with `fig.legend(loc="outside upper center")` under constrained layout.
- Limit decimals with `ax.ticklabel_format` or formatters; avoid overlapping tick labels rather than rotating them when you can reduce the tick count (`ax.locator_params(nbins=5)`).

## 6. Color and accessibility

- Sequential data: `viridis` (default) or `cividis`, both perceptually uniform and readable with common color-vision deficiencies. Avoid `jet` and `rainbow`.
- Diverging data: recent Matplotlib versions ship `berlin`, `managua` and `vanimo`; classic choices such as `coolwarm` also exist. Center the scale with `matplotlib.colors.TwoSlopeNorm` or `CenteredNorm`.
- Categorical colors: the styles `petroff10` and `tableau-colorblind10` are shipped in 3.11.2 (`petroff6` and `petroff8` as well). Load one with `plt.style.use("petroff10")`; it sets the color cycle.
- Never rely on color alone: vary `linestyle`, `marker` and direct labels so the figure works in grayscale print. Check with `plt.style.use("grayscale")` or a color-vision simulator.
- Keep one color per quantity across all figures in the paper.
- Use the same colormap and `vmin`/`vmax` across panels that are meant to be compared.
- For the image-like panels, `imshow(..., interpolation="nearest")` or `pcolormesh(..., rasterized=True)` keeps discrete data honest.

## 7. Dense data in vector files

- A scatter plot of 100,000 points saved as PDF becomes a huge file that is slow to open. Set `rasterized=True` on the artist: the points become an embedded raster while axes, labels and text stay vector.
- `ax.set_rasterization_zorder(z)` rasterizes everything below the given zorder.
- Alternatives: hexbin (`ax.hexbin`), 2D histogram (`ax.hist2d`), or a downsampled line (`np.interp` on a reduced grid), which is also easier to read.
- Check file size: figures above a few MB are usually over-detailed for a paper.
- For line plots with millions of points, decimate or aggregate before plotting; Matplotlib draws every vertex.

## 8. Figure script template

```python
"""Regenerate Figure 2 from results/run.npz."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]      # scripts/make_figures.py -> project root
MM = 1.0 / 25.4
COLUMN = 86 * MM          # replace with the journal's single-column width

plt.style.use(["petroff10", str(ROOT / "styles" / "paper.mplstyle")])


def main() -> None:
    data = np.load(ROOT / "results" / "run.npz")         # allow_pickle stays False
    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=(2 * COLUMN, 0.7 * COLUMN), layout="constrained"
    )
    ax_a.plot(data["t"], data["y"], label="model")
    ax_a.set(xlabel="Time (s)", ylabel="Amplitude (a.u.)")
    ax_a.legend()
    im = ax_b.imshow(data["field"], cmap="cividis", origin="lower")
    fig.colorbar(im, ax=ax_b, label="Field (a.u.)")
    for label, ax in zip("ab", (ax_a, ax_b)):
        ax.text(0.0, 1.02, f"({label})", transform=ax.transAxes, fontweight="bold")
    out = ROOT / "figures"
    out.mkdir(exist_ok=True)
    fig.savefig(out / "fig2.pdf", metadata={"CreationDate": None})
    plt.close(fig)


if __name__ == "__main__":
    main()
```

- Run with `MPLBACKEND=Agg python scripts/make_figures.py` in a clean environment or CI job, and commit the script, not only the output.
- Add the script's data inputs to the repository or document how to regenerate them.

## 9. Checklist before submission

- [ ] Figure size equals the printed size; text 6 to 9 pt at that size.
- [ ] PDF or SVG for line art; fonts embedded (Type 42 or outlines).
- [ ] Rasterized dense layers; file size reasonable.
- [ ] Colors readable in grayscale and for color-vision deficiency; colormap perceptually uniform.
- [ ] Axis labels, units, panel labels and legends complete; no title inside the figure when the caption carries it.
- [ ] Identical styling across all figures (same style file).
- [ ] Script regenerates each file with one command.
