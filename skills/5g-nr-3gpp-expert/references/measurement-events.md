# Measurement Events and Filtering

How an NR UE is configured to measure and report, what events A1 to A6 and B1 and B2 mean, how hysteresis, time-to-trigger and filtering shape the trigger instant, and how to map these to simulation parameters. No clause numbers are given because the specification text was not fetched; see TS 38.331 (measurement configuration and reporting), TS 38.215 (quantities) and TS 38.133 (measurement requirements) for exact text.

## Contents

1. [Configuration structure](#1-configuration-structure)
2. [Measured quantities](#2-measured-quantities)
3. [Events in words](#3-events-in-words)
4. [Hysteresis, offsets and time-to-trigger](#4-hysteresis-offsets-and-time-to-trigger)
5. [L1 and L3 filtering](#5-l1-and-l3-filtering)
6. [Periodic and other reporting](#6-periodic-and-other-reporting)
7. [Measurement timing and gaps](#7-measurement-timing-and-gaps)
8. [Mapping to a simulator](#8-mapping-to-a-simulator)
9. [Worked reasoning examples](#9-worked-reasoning-examples)

## 1. Configuration structure

The network sends a measurement configuration (`MeasConfig`) in an RRC reconfiguration. Its main parts:

| Part | Role |
|---|---|
| Measurement objects (`measObjectNR`) | A carrier frequency to measure, with the reference signals (SSB timing through `smtc1`, `smtc2`, or CSI-RS resources), subcarrier spacing, and per-cell offsets and black or white lists |
| Report configurations (`reportConfigNR`) | Trigger type (event, periodic, others), the event with its thresholds, hysteresis, `timeToTrigger`, the quantity that triggers (RSRP, RSRQ, SINR), what to report, `reportInterval`, `reportAmount`, `maxReportCells` |
| Measurement identities (`measId`) | Links one object to one report configuration. One UE can run many identities in parallel |
| Quantity configuration (`quantityConfig`) | L3 filter coefficients per quantity, and for SSB or CSI-RS based measurement |
| Other | `s-MeasureConfig` (neighbour measurements only run when serving quality is below a threshold), `measGapConfig` (gaps for inter-frequency measurement) |

- Field names above are from memory of the ASN.1 module; confirm them, their value sets and units in the current TS 38.331.
- Intra-frequency measurements run when the neighbour SSB lies inside the UE's active bandwidth part and the SMTC window; inter-frequency measurements may need gaps, depending on UE capability.
- Events are evaluated per measurement identity and per cell. The UE keeps a list of cells that satisfy the entering condition.

## 2. Measured quantities

TS 38.215 defines the physical layer measurements. Quantities used in mobility:

| Quantity | Meaning in words |
|---|---|
| SS-RSRP | Linear average of the power of the resource elements carrying the secondary synchronisation signal (the PBCH DM-RS may be included). Reported in dBm after mapping |
| SS-RSRQ | Ratio of SS-RSRP, scaled by the number of resource blocks in the measurement, to the carrier RSSI measured over the configured symbols. Depends on load and on the RSSI measurement window |
| SS-SINR | Ratio of SS-RSRP to the linear average of interference plus noise power over the same resource elements |
| CSI-RSRP, CSI-RSRQ, CSI-SINR | The same ideas for CSI-RS resources, used for beam-level and mobility measurements when configured |
| L1-RSRP | Beam-level measurement reported in CSI reports for beam management (see beam-management-ssb.md) |

- RSRP is a per-resource-element power, so it does not depend on bandwidth; RSRQ depends on bandwidth and load, so two cells with equal RSRP can have different RSRQ.
- SS-RSRP of a cell may be derived from several SS/PBCH blocks (beams). The consolidation rule is configured; see section 3 of beam-management-ssb.md.
- Reporting mapping (dB to integer index) has ranges and step sizes in TS 38.133. Reported values are quantised; simulations that report floating point values overstate resolution.
- SS-SINR is not available for every measurement setup; check the report configuration and UE capability.

## 3. Events in words

Serving cell here means the special cell (SpCell) unless the event says SCell. The exact entering and leaving expressions, including every offset term, are in TS 38.331; the descriptions below are the semantics.

| Event | Entering condition (semantic) | Typical use |
|---|---|---|
| A1 | Serving becomes better than a threshold | Stop inter-frequency measurements, release gaps |
| A2 | Serving becomes worse than a threshold | Start inter-frequency measurements, trigger coverage-based actions |
| A3 | Neighbour becomes offset better than the SpCell | Intra-frequency handover, best-cell triggering |
| A4 | Neighbour becomes better than a threshold | Load-based or layer-based handover, SCell or PSCell candidate |
| A5 | SpCell worse than threshold 1 and neighbour better than threshold 2 | Coverage-based inter-frequency handover |
| A6 | Neighbour becomes offset better than an SCell | Intra-frequency SCell change in carrier aggregation |
| B1 | Inter-RAT neighbour better than a threshold | Handover to another RAT |
| B2 | Serving worse than threshold 1 and inter-RAT neighbour better than threshold 2 | Coverage-based inter-RAT handover |

- Each event has its own leaving condition, which uses the hysteresis in the opposite direction. The pair prevents toggling around a threshold.
- A3 compares two cells directly, so a common bias (for example, a UE-side power offset) cancels; thresholds in A4 and A5 do not cancel it.
- The offset in A3 can be positive or negative. A negative offset makes the UE report before the neighbour is as strong as the serving cell, which is used for early handover.
- Cell individual offset and frequency offset enter A3 through the measurement object; the network can use them to bias a particular cell without touching the report configuration.
- Newer releases add events for other purposes (for example time-based and distance-based conditional events for non-terrestrial networks, and L1-based events for L1/L2 mobility). Check the current TS 38.331 and the release notes of the study.

## 4. Hysteresis, offsets and time-to-trigger

Three parameters shape the trigger instant:

- Hysteresis (`hysteresis`): a dB margin that makes entering harder and leaving harder, so the two conditions are separated by a band. Check in TS 38.331 exactly how it enters each condition, and how the simulator applies it.
- Time-to-trigger (`timeToTrigger`): the entering condition must hold without interruption for this long before the UE sends a report. If the leaving condition holds before it expires, the timer is cancelled. The value set is discrete, from 0 ms up to several seconds; read it from the ASN.1.
- Offset (`a3-Offset`): the margin by which the neighbour must beat the SpCell. The ASN.1 unit is a fraction of a dB; confirm the step.

Behaviour to expect:

| Change | Effect on handovers | Effect on failures |
|---|---|---|
| Larger TTT | Later, fewer handovers, fewer ping-pongs | More too-late handovers at high speed |
| Larger hysteresis | Later, fewer handovers | Same direction as TTT |
| Larger A3 offset | Later handover point | More too-late failures |
| Negative A3 offset | Earlier handover | More too-early and ping-pong |
| Heavier L3 filtering | Smoother trace, delayed response | More too-late failures at high speed |

- The effective handover point is the cell-edge position where the filtered, offset-adjusted comparison has been true for TTT, plus the reporting, decision, preparation and execution delays.
- Because the shadowing correlation distance sets how fast the signals fluctuate, the same TTT behaves differently at 3 km/h and at 120 km/h. Always report speed.
- A rough sanity check: the distance travelled during TTT is speed times TTT. If this distance is a large fraction of the cell-edge overlap region, expect too-late failures.

## 5. L1 and L3 filtering

Two filtering stages sit between the radio signal and the event evaluation:

1. L1 filtering. The physical layer averages power samples across an evaluation period. It is implementation dependent, but TS 38.133 gives accuracy requirements and evaluation periods, which depend on the SMTC periodicity, DRX cycle and frequency range.
2. L3 filtering. RRC applies a configured first-order recursive (exponential) filter on the measurement result of each quantity. The coefficient is configured per quantity (RSRP, RSRQ, SINR) in the quantity configuration; a value of 0 gives no filtering. Higher coefficients mean heavier smoothing. The relation between the coefficient and the filter weight, and the sampling interval of the filter input, are given in TS 38.331. Do not reconstruct them from memory.

Practical points:

- The filter input rate is the L1 output rate, not the simulator time step. A filter applied once per simulation tick has a different time constant from the standard's.
- A time constant in seconds is approximately the sampling interval divided by the weight, for small weights. Heavy filtering plus long TTT adds delays that stack.
- The filter works on the quantity value as defined by the standard; some implementations filter in the dB domain, others in linear. State the choice, and test sensitivity if it matters.
- Filter state handling at handover and at cell changes is defined in TS 38.331 (check the text); simulations that carry stale filter state across cells can distort the first reports after handover, so state what was done.
- Beam-level L1 measurements are processed differently from cell-level L3 measurements; keep them separate in code.

## 6. Periodic and other reporting

- Periodic reports send the strongest cells every `reportInterval` for `reportAmount` times (including infinity). They are used when the network wants to run its own decision algorithm instead of a UE-side event.
- Event reports can also be repeated every `reportInterval` while the condition holds, up to `reportAmount`. Setting the amount to 1 sends a single report.
- `maxReportCells` limits the number of cells in a report, and `reportQuantityCell` selects which quantities (RSRP, RSRQ, SINR) are included.
- With `reportOnLeave`, a report is also sent when the leaving condition is met (check the current ASN.1 and release for availability).
- The network can request per-beam results in addition to per-cell results (`reportQuantityRS-Indexes`, `maxNrofRS-IndexesToReport`, `includeBeamMeasurements`).
- Reports go via SRB1 and take time for scheduling and delivery. A simulation that applies the handover decision in the same tick as the trigger removes this delay.

## 7. Measurement timing and gaps

- The UE measures SSBs only inside the configured SMTC window, so a neighbour with a long SMTC periodicity can be sampled rarely.
- Inter-frequency measurements may require measurement gaps in which the UE cannot send or receive data. Gap pattern and length affect throughput; study them if the work compares inter-frequency schemes.
- DRX lengthens the measurement period, since the UE measures only during active time or according to the rules in TS 38.133. Idle and inactive measurement relaxations are in TS 38.304.
- Measurement requirements (delays, accuracy) are in TS 38.133 by number; if you need a specific evaluation period, read it from the current version rather than from a paper.
- Layer 1 measurement for L1/L2 mobility uses CSI reporting machinery and has its own timing; see handover-cho.md.

## 8. Mapping to a simulator

Typical gaps between the standard and a simulator, and how to document them:

| Standard behaviour | Common simplification | What to state |
|---|---|---|
| L1 averaging over several SSB bursts | One sample per tick | Sample interval, number of samples averaged |
| Quantised reported values | Floating point | That reports are not quantised |
| Reporting through SRB1 with scheduling delay | Immediate | Delay assumed |
| SMTC window and gaps | Always measuring | That SMTC is ignored |
| Beam-to-cell consolidation | Best beam | Consolidation rule |
| Per-cell offsets | Absent | Value zero |
| Handover preparation and random access | Fixed interruption time | The fixed value |

- Name the simulator parameter next to each spec parameter in a mapping note, so reviewers can see what is modelled.
- For ns-3 or MATLAB implementations, defer to ns3-expert or matlab-expert for API details.

## 9. Worked reasoning examples

Reasoning with symbols, not spec numbers:

- A UE moves at speed v across an overlap region of length d. If TTT plus total handover delay T_total satisfies v times T_total larger than d, the UE leaves the source coverage before the handover completes. Choose parameters so that T_total is below d divided by v for the target speed range.
- A negative A3 offset moves the crossing point toward the source cell, a positive one toward the target cell. The size of the shift in metres depends on the path loss slope near the border; shadowing makes the real crossing noisy, so use this for intuition only.
- If shadow fading has standard deviation sigma and the correlation distance is d_corr, the number of spurious A3 crossings across the border grows when v times TTT is much smaller than d_corr and sigma is large compared with hysteresis. Increase hysteresis or TTT, or filter, until the spurious rate meets the target.
- When comparing two filter settings, look at the delay of the filtered trace at a step change and the variance of the filtered trace on a stationary input; the best setting depends on the speed range.
