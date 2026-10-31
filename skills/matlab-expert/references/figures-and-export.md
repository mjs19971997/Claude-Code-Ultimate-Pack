# Figures and Export for Papers

Producing publication-quality MATLAB figures and exporting them with `exportgraphics`: sizing, layout with `tiledlayout`, fonts, colour, vector versus raster output, and reproducible plotting code. Calls shown are long-standing graphics functions (`exportgraphics` since R2020a, `tiledlayout` since R2019b); check the release notes if you target an older release.

## Contents

1. [Principles](#1-principles)
2. [Figure size and layout](#2-figure-size-and-layout)
3. [exportgraphics](#3-exportgraphics)
4. [Fonts, lines and labels](#4-fonts-lines-and-labels)
5. [Colour](#5-colour)
6. [Vector versus raster](#6-vector-versus-raster)
7. [Reproducible plotting code](#7-reproducible-plotting-code)
8. [Other output paths](#8-other-output-paths)

## 1. Principles

- Create the figure at the final printed size (for example 8.5 cm for a single IEEE column, or the journal width), then use font sizes that are readable at that size (commonly 8 to 10 pt). Scaling a large figure down afterwards shrinks the text unpredictably.
- Write one function per figure that takes data and returns the figure handle. The script that calls it saves the file. Re-running the function regenerates the file exactly.
- Export line plots as vector PDF or EPS, images and dense scatter plots as raster PNG at 300 dpi or higher, and keep the source data (`.mat` or `.csv`) next to the figure.
- Check the journal or template instructions for accepted formats, fonts, colour mode and minimum line width before exporting; they differ.
- Never use screenshots or `saveas` with default sizes for figures that go into a paper.

## 2. Figure size and layout

```matlab
function fig = plotBerCurves(snrDb, ber, labels)
    arguments
        snrDb (:,1) double
        ber (:,:) double
        labels (1,:) string
    end
    fig = figure(Units="centimeters", Position=[2 2 8.5 6.5], Color="w");
    ax = axes(fig);
    semilogy(ax, snrDb, ber, LineWidth=1.2, Marker="o", MarkerSize=4);
    grid(ax, "on");
    xlabel(ax, "SNR (dB)");
    ylabel(ax, "Bit error rate");
    legend(ax, labels, Location="southwest", Box="off");
    ylim(ax, [1e-6 1]);
end
```

- `figure(Units="centimeters", Position=[left bottom width height])` fixes the on-screen window size; `exportgraphics` writes the figure at that size for vector formats.
- For multi-panel figures use `tiledlayout`, which handles spacing and shared labels:

```matlab
fig = figure(Units="centimeters", Position=[2 2 17.5 6], Color="w");
t = tiledlayout(fig, 1, 3, TileSpacing="compact", Padding="compact");
for k = 1:3
    ax = nexttile(t);
    plot(ax, x, y(:, k), LineWidth=1.1);
    title(ax, "(" + char('a' + k - 1) + ")");
end
xlabel(t, "Time (s)");
ylabel(t, "Amplitude");
```

- `nexttile(t, [rowSpan colSpan])` creates larger tiles, `title(t, ...)`, `xlabel(t, ...)` and `ylabel(t, ...)` label the whole layout. Use `tiledlayout("flow")` when the number of panels varies.
- Use `axis tight`, `xlim`, `ylim` and `xticks` explicitly; leave no auto-ranges that change when data change.
- Use `subplot` only when maintaining old code; its spacing control is weaker.
- Set `ax.Layer = "top"` when grid lines must lie above filled graphics, and `ax.Box = "on"` for closed frames.

## 3. exportgraphics

```matlab
exportgraphics(fig, "ber.pdf", ContentType="vector");                  % vector PDF
exportgraphics(fig, "ber.eps", ContentType="vector");                  % vector EPS
exportgraphics(fig, "ber.png", Resolution=300);                        % raster, 300 dpi
exportgraphics(ax,  "panel.png", Resolution=600, BackgroundColor="none");  % axes only, transparent
exportgraphics(fig, "multi.pdf", Append=true);                         % add a page to a PDF
exportgraphics(t,   "layout.pdf", ContentType="vector");               % a tiledlayout
```

- First argument: a figure, axes, `tiledlayout`, or other graphics container. Second argument: file name; the extension selects the format (`.pdf`, `.png`, `.jpg`, `.tif`, `.gif`, `.eps`, `.emf` on Windows).
- `ContentType` is `"auto"` (default), `"vector"` or `"image"`. `"vector"` keeps lines and text as paths; `"image"` rasterises the whole figure.
- `Resolution` sets dots per inch for raster output and for rasterised content in vector files. 300 dpi is a common minimum for print; use 600 dpi for line art in raster formats.
- `BackgroundColor` accepts a colour or `"none"` for transparency (formats permitting). `Padding` (for example `"tight"`) controls the margin around axes in recent releases; check `doc exportgraphics` for supported values in your release.
- `copygraphics(fig)` copies a figure to the clipboard for documents, with the same content-type options.
- Axes exports crop to the axes outer position, which is useful for individual panels of a multi-panel figure.
- Export in a script after all properties are set, and avoid `drawnow`-dependent timing; calling `drawnow` before export is cheap and removes pending-update surprises.
- For automated batches, loop over figure functions and export with consistent names; close each figure afterward with `close(fig)` to free memory.

## 4. Fonts, lines and labels

```matlab
set(groot, "defaultAxesFontName", "Helvetica", ...
           "defaultAxesFontSize", 9, ...
           "defaultTextFontName", "Helvetica", ...
           "defaultLineLineWidth", 1.2);
xlabel(ax, "$E_b/N_0$ (dB)", Interpreter="latex");
ax.TickLabelInterpreter = "latex";
```

- Set defaults in one function (`setPaperDefaults`) that the figure functions call; reset with `reset(groot)` afterwards if the session is shared.
- Pick a font that exists on every machine that builds the figure and match the paper body (Helvetica or Arial for sans-serif; for serif, Times New Roman or the font your template specifies). `listfonts` shows installed fonts.
- `Interpreter="latex"` uses MATLAB's own LaTeX renderer, not a TeX installation, and supports a subset of commands. For fully matching fonts, some authors export a figure without text and typeset labels in LaTeX; the third-party matlab2tikz or similar tools generate TikZ/PGFPlots code. Evaluate the licence and maintenance status of third-party tools before adopting.
- Use at least 0.5 pt line width and avoid dotted lines for important curves. Distinguish series by line style and marker as well as colour so a greyscale print is readable.
- Use `fontsize(fig, 9, "points")` to rescale text in a figure (check the release that added it; it is recent) or set sizes explicitly in your plotting function.
- Put units in labels (`"Frequency (GHz)"`), keep legends short, and use `legend(..., Box="off")` to save space.

## 5. Colour

- Avoid the retired `jet` colormap for continuous data: it is perceptually non-uniform. `parula` is the default; `turbo` offers a wider range but needs care; use sequential maps for ordered data and diverging maps with a meaningful midpoint.
- For categorical series use `colororder(ax, colors)` or `ax.ColorOrder`. Choose colours that stay distinguishable under common colour-vision deficiencies and in greyscale; test by converting the figure to greyscale.
- Pass an RGB matrix for custom palettes (values 0 to 1). Store palettes in one function so all figures agree.
- Set `fig.Color = "w"` and use black axes for print. For slides, matching a dark theme is a separate styling pass, not the default.
- `colorbar` needs a label with units: `cb = colorbar(ax); cb.Label.String = "Power (dBm)";`.
- Light and dark themes: recent releases support graphics themes; check the release notes and `doc theme` before using them in export code, because exported colours depend on the active theme.
- Keep CMYK requirements in mind: MATLAB exports RGB. If a publisher requires CMYK, convert in a separate tool and check that the colours still read well.

## 6. Vector versus raster

- Vector output scales without loss and keeps text selectable, and is the right choice for line plots, bar charts and block diagrams.
- Dense content (a scatter plot of 1e6 points, a surface with a fine mesh, a spectrogram) makes vector files huge and slow. Options: export as `ContentType="image"` at 300 to 600 dpi; or plot with `scatter` and then rasterise only that layer by exporting the plot area as an image and combining it with vector axes in a vector editor.
- `imagesc`, `image` and `imshow` content is already raster; in a vector PDF it is embedded at its native resolution, which can look soft when enlarged. Interpolate or resample deliberately and check at 100 percent zoom.
- 3-D surfaces and lighting are rendered by the graphics system; transparency and shading may rasterise the plot even if you request vector. Inspect the PDF at high zoom.
- Test the exported file in the target toolchain (LaTeX `\includegraphics`, word processor, journal submission checker). Look for missing fonts, clipped labels and broken transparency.
- File size matters: if a PDF is more than a few MB, reduce data points (plot every Nth point, aggregate, plot envelopes) before exporting.

## 7. Reproducible plotting code

- Store results (`save(file, "snrDb", "ber", "-v7")`) separately from the plotting function. The figure script loads results and plots them; changing a label then needs no simulation re-run.
- Record the MATLAB release and the seed in the saved results (`struct("release", version("-release"), "seed", seed)`), and print them into the log.
- Do not rely on interactive edits (property inspector, plot tools). If a tweak is needed, put it in code.
- Name output files after the figure number or key used in the manuscript, and write them to a `figures/` folder created by the script (`mkdir`).
- Make the figure function deterministic: avoid random jitter and sort grouped data before plotting.
- Version control the `.m` files and, for small figures, the exported `.pdf`; large binary outputs belong in release assets or a data repository.
- Add a build task that regenerates all figures (see [testing-and-build.md](testing-and-build.md)) so the artefacts can be rebuilt from clean data.
- For testing, create the figure with `Visible="off"` and verify properties (axis labels, limits, number of lines) rather than comparing image bytes.

## 8. Other output paths

- `print(fig, "name", "-dpdf", "-painters")` and `print(fig, "name", "-dpng", "-r300")` remain valid, and `-painters` forces the vector renderer. Prefer `exportgraphics` for new code, since its sizing and cropping behaviour are more predictable.
- `saveas(fig, "name.png")` captures at screen resolution and is not suited to publication output.
- `savefig` and `openfig` store the figure as `.fig`; a `.fig` file is a MATLAB-version-dependent binary, so keep the plotting code and data as the source of truth.
- `exportapp` (for apps) and `getframe`/`VideoWriter` (for animations) are separate APIs; for animations, write frames with `VideoWriter` and a documented profile.
- Table output for papers: `writetable` for CSV, and for LaTeX tables generate text with `compose` or `fprintf` from the data, so numbers in the paper come from the same run as the figures.
- The LaTeX side of figure inclusion (widths, `\includegraphics`, caption conventions) belongs to latex-academic-expert; the manuscript structure belongs to scientific-writing-expert.
