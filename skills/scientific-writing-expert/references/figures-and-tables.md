# Figures, Tables, Notation and Reproducibility

Figures, tables and symbols as writing artefacts: what each must say, how to caption, label and colour them, how to keep notation consistent, and how to write an artifact statement. Plotting code belongs to scientific-python-expert and matlab-expert; LaTeX float and table syntax to latex-academic-expert.

## Contents

1. [One message per figure](#1-one-message-per-figure)
2. [Captions that stand alone](#2-captions-that-stand-alone)
3. [Axes, labels and units](#3-axes-labels-and-units)
4. [Colour and accessibility](#4-colour-and-accessibility)
5. [Choosing the chart](#5-choosing-the-chart)
6. [Tables](#6-tables)
7. [Interpreting figures in the text](#7-interpreting-figures-in-the-text)
8. [Notation consistency](#8-notation-consistency)
9. [Reproducibility and artifact statements](#9-reproducibility-and-artifact-statements)
10. [Checks](#10-checks)

## 1. One message per figure

- State the message of each figure as a sentence before making it: "The fallback keeps the outage rate flat above 60 km/h." If you need "and" twice, split the figure.
- Remove anything that does not serve the message: gridlines in excess, redundant legends, curves that do not support the comparison.
- Order panels logically (left to right, top to bottom) and label them (a), (b), (c); refer to them as "Fig. 4(b)".
- Keep a consistent visual identity: the same method has the same colour, marker and line style in all figures and tables.
- Use block diagrams for systems and architectures; keep boxes few, arrows labelled with what flows, and the same terms as the text.
- Reuse of a figure from another source requires permission and a credit line; redraw and cite as "adapted from [n]" only with permission.

## 2. Captions that stand alone

A reader skimming the figures should understand each one without reading the text.

Pattern: what is shown, under which conditions, how to read it, and the takeaway.

```text
Before:  Fig. 5. Results.
After:   Fig. 5. Median beam misalignment versus user speed for the proposed
         tracker, exhaustive sweeping and the recurrent baseline (28 GHz,
         64-element array, 200 runs per point). Shaded areas are the 10th to
         90th percentile range. The proposed tracker stays below 1 degree up
         to 120 km/h.
```

- IEEE style puts figure captions below figures and table captions above tables, and uses the abbreviation "Fig." and roman numerals for tables in many IEEE journals; the venue template decides, so check the manual and template.
- Start the caption with a noun phrase, not a sentence beginning "This figure shows".
- Define abbreviations and symbols used in the figure, unless they are defined in the caption of a previous figure and the venue permits.
- State what error bars or shaded areas mean and the number of runs.
- Alt text and long descriptions are required by some publishers and good practice for accessibility; provide them if the submission system asks.

## 3. Axes, labels and units

- Label each axis with the quantity and the unit: "Throughput (Mbit/s)", "SNR (dB)", "Distance (m)". Dimensionless quantities say so ("Normalised load").
- Use the symbol and unit conventions of the paper; do not mix "ms" in the figure and "s" in the text for the same quantity without conversion.
- Font size in the figure at final column width should be close to the body text size, never smaller than about 7 to 8 points after reduction.
- Line width at least about 1 point; markers visible but not overwhelming; limit marker count with a marker interval.
- Use logarithmic axes when data span orders of magnitude, label them as such, and use a log scale for error-rate curves.
- Start bar chart axes at zero. Line charts may start elsewhere when the trend is the point, but a truncated axis must be visible.
- Do not rely on titles inside the plot; the caption is the title. Legends sit inside the plot area where space allows and have readable entries in the order of the curves.
- Export vector graphics (PDF, EPS, SVG) for line art and high-resolution raster for photos or heatmaps, as the venue requires.
- Avoid screenshots of plots from tools; regenerate at the correct size.

## 4. Colour and accessibility

- Assume that some readers are colour-blind (roughly 1 in 12 men) and that many print in grayscale. Colour must never be the only cue.
- Use a colour-blind-safe qualitative palette such as the Okabe-Ito set (eight colours designed to be distinguishable under common forms of colour-blindness), and add a second encoding: marker shape, line style or direct labels.
- Use perceptually uniform sequential maps (for example viridis family) for heatmaps and avoid the rainbow map; diverging maps only when there is a meaningful midpoint.
- Keep to four to six series per panel; beyond that, split the panel or use small multiples.
- Check contrast: light colours on white (yellow) vanish in print. Test the figure by converting to grayscale.
- Use direct labels on curves when there are few series; they reduce the legend lookup.
- Keep colours consistent across figures: baseline A is always the same colour.
- Plotting libraries and palette code: scientific-python-expert, matlab-expert.

## 5. Choosing the chart

| Message | Usual chart | Notes |
|---|---|---|
| Trend versus a continuous variable | Line plot with markers | Show variability |
| Comparison across a few categories | Bar chart or dot plot | Zero baseline for bars; sort by value if no natural order |
| Distribution | Histogram, empirical CDF, box plot | CDFs compare distributions well; state the sample size |
| Relationship of two variables | Scatter plot | Add fit only if it supports a claim |
| Error rates and tails | Semi-log plot | Mark the target level |
| Spatial or matrix data | Heatmap | Perceptually uniform map and colour bar with units |
| System structure | Block diagram | Few boxes, labelled arrows |
| Timeline or protocol | Sequence or timing diagram | Match message names to the text or standard |

- Avoid 3D charts and pie charts for quantitative comparison.
- Do not draw a line through points that are not a continuous function (discrete configurations): use markers or bars.
- Plot raw points when n is small; summaries hide structure.

## 6. Tables

- Use tables for exact values, many methods against many metrics, parameter lists and notation.
- Caption states the content and conditions; put units in column headers, not in each cell.
- Align decimal points, use the same number of decimals within a column, and choose significant digits that match the measurement precision.
- Mark the best result in each column consistently (bold) and state the rule in the caption, including ties; show variability (for example mean and standard deviation) in the same cell format throughout.
- Order rows logically (baselines first, then the proposed method) and separate groups with spacing or rules, not with many vertical lines.
- Parameter tables list symbol, meaning, value and unit; cite the source of each value that comes from a standard or an earlier work.
- Do not let a table run to more than about a half page in a two-column paper; move the rest to an appendix.
- Summary statistics, tests and intervals: statistics-expert.

## 7. Interpreting figures in the text

Each figure needs a paragraph that does four things:

1. Points to it by label and says what to look at.
2. States the observation with numbers.
3. Explains why it happens, linking to the model or mechanism.
4. Notes a caveat or a link to the next result.

```text
Fig. 5 shows that the proposed tracker keeps the median misalignment below
1 degree up to 120 km/h, whereas the recurrent baseline exceeds 2 degrees
above 60 km/h. The baseline's history window no longer covers the angular
change per update at those speeds; the confidence test of Section 4.2 detects
this and triggers the local sweep. The price is a higher overhead above
90 km/h, quantified in Table III.
```

- Do not describe every point of a curve; describe the pattern and the exceptions.
- Do not leave a figure that the text never mentions.

## 8. Notation consistency

- Keep a notation table in the system-model section when there are more than about 15 symbols; keep a project-level glossary during drafting.
- One symbol, one meaning; one concept, one symbol. Check subscripts and superscripts for the same pattern across sections (for example `P_t` for transmit power everywhere).
- Fix a typographic convention and state it once: scalars in italic, vectors bold lowercase, matrices bold uppercase, sets calligraphic, operators upright (`\max`, `\mathrm{d}`).
- Follow the symbol conventions of the standard or of the community when they exist (for example the symbols of a 3GPP specification: 5g-nr-3gpp-expert), and note any deviation.
- Define every symbol next to the equation where it first appears; do not rely on a distant table only.
- Use the same name for the same thing in text, figures, tables and code. "Handover", "handoff" and "HO" in one paper confuse readers.
- Dimensional consistency: state units for constants and parameters; check that equations are dimensionally consistent.
- Limit the use of Greek letters for unrelated quantities; avoid symbols that are visually close (l, 1, I; v, nu).

## 9. Reproducibility and artifact statements

Methods section details:

- Software and hardware: versions of simulators, frameworks, compilers and operating systems; CPU, GPU, memory where timing is reported.
- Data: source, licence, size, preprocessing, train, validation and test splits, and how leakage is avoided.
- Parameters: all values that affect results, in a table, plus how they were chosen.
- Randomness: seeds or the number of independent runs, and the aggregation method.
- Baselines: source code or implementation description, configuration and tuning budget.

Artifact or data availability statement (adapt to the venue's template):

```text
Code, configuration files and the scripts that generate Figs. 4 to 8 are
available at <persistent link> (version <tag or commit>, licence <name>).
The measured channel traces are available at <persistent link> under
<licence>. The production trace used in Section 5.3 cannot be released
because of a confidentiality agreement; a synthetic trace with matching
statistics and the generator are included. Experiments ran on <hardware
description>; the full run takes about <time>.
```

- Use a persistent identifier (an archive deposit with a DOI) for released artifacts rather than a plain repository link only; tag the exact version used in the paper.
- State what is not released and why; do not leave silence.
- Include a licence for code and for data; check the licence of datasets you reuse.
- For anonymous review, use an anonymised artifact link if the venue allows and remove identifying metadata.
- Some venues run artifact evaluation with badges (available, functional, reproduced); read the call for the exact criteria and timeline.
- Test the artifact on a clean machine or container before submission: the instructions, the dependency list and a smoke test that finishes in minutes.

## 10. Checks

- Every figure and table is cited in order of first appearance and interpreted.
- Print the paper in grayscale at final size; all series remain distinguishable and text remains legible.
- Search for each symbol and abbreviation: defined once, used consistently.
- Compare numbers in the text with those in the tables and plots.
- Confirm that the caption of each figure can be understood alone.
- Confirm permissions and credit lines for any third-party figure.
- Confirm the artifact statement links and that the tagged version reproduces the main figure.
