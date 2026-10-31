---
name: 5g-nr-3gpp-expert
description: >-
  Explains and analyses 5G NR mobility and handover for researchers and engineers: measurement events A1 to A6, A3 offset, time-to-trigger and hysteresis, L1 and L3 filtering, conditional handover (CHO), RRC states, SSB and CSI-RS beam management, SS-RSRP, SS-RSRQ and SS-SINR, and the TR 38.901 channel models. Use when reading TS 38.300, 38.331, 38.133 or 38.215, tuning handover parameters, or interpreting handover failures and ping-pong in simulation output. Not for simulator code (use ns3-expert), MATLAB code (use matlab-expert), paper writing (use scientific-writing-expert), or statistics (use statistics-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# 5G NR 3GPP Expert

This skill covers the 5G NR radio access network from the point of view of someone who simulates or analyses mobility: how a UE measures cells, when it reports, how the network decides on a handover, what can go wrong, and which channel model and beam assumptions sit under the numbers. It explains the standard's concepts and parameters and how to map them to simulation settings. Simulator code, MATLAB code, paper text and statistical testing belong to other skills.

> Verified against: no 3GPP specification text could be fetched in this session (www.3gpp.org, portal.3gpp.org and www.etsi.org were not reachable), so no spec version is claimed and no clause or table numbers are cited. Specs are named by number only (TS 38.300, TS 38.331, TS 38.133, TS 38.215, TS 38.304, TR 38.901). Release status (Release 19 frozen in December 2025, Release 20 under way) comes from web search summaries only (2026-10).

## Contents
1. [Scope](#1-scope)
2. [Core Expertise](#2-core-expertise)
3. [Workflow](#3-workflow)
4. [Decision Rules](#4-decision-rules)
5. [Coding Standards](#5-coding-standards)
6. [Project Structure](#6-project-structure)
7. [Design Patterns](#7-design-patterns)
8. [Best Practices](#8-best-practices)
9. [Performance](#9-performance)
10. [Security](#10-security)
11. [Testing](#11-testing)
12. [Review Checklist](#12-review-checklist)
13. [Production Notes](#13-production-notes)
14. [Examples](#14-examples)
15. [Common Mistakes](#15-common-mistakes)
16. [References](#16-references)

## 1. Scope

- Covered: NR RRC states and the procedures that matter for mobility (setup, reconfiguration with sync, re-establishment, resume), measurement configuration and reporting (measurement objects, report configurations, measurement identities), event-triggered reporting A1 to A6 and the inter-RAT events B1 and B2, time-to-trigger, hysteresis and offsets, L1 and L3 filtering, handover and conditional handover, radio link failure and failure classification, SSB and CSI-RS based beam management, the measurement quantities SS-RSRP, SS-RSRQ and SS-SINR, and the TR 38.901 channel models as used for link and system studies.
- Not covered: writing ns-3 or 5G-LENA code (ns3-expert); MATLAB or 5G Toolbox scripts (matlab-expert); structuring or wording a paper (scientific-writing-expert); confidence intervals, hypothesis tests and sample-size questions (statistics-expert); generic data wrangling of result files (data-analysis-expert); training ML handover models (pytorch-expert, ml-engineering-expert).
- Core network, slicing, security architecture and the physical layer waveform are only touched where they affect mobility.
- Rule for this skill: clause and table numbers are cited only from specification text that was read in the same session. When the text was not available, name the spec ("see TS 38.331, measurement report triggering") and tell the reader to check the current version.

## 2. Core Expertise

| Area | Key facts |
|---|---|
| RRC states | RRC_IDLE, RRC_INACTIVE and RRC_CONNECTED. Mobility in connected mode is network controlled (measurement report, then reconfiguration with sync). In idle and inactive the UE performs cell reselection by itself using the rules in TS 38.304 and system information. Inactive keeps the UE context in the network and uses RRCResume |
| Measurement framework | Configuration (in TS 38.331) has measurement objects (what frequency and reference signals), report configurations (when and what to report) and measurement identities that link the two. Quantities: RSRP, RSRQ and SINR, based on SS/PBCH block or CSI-RS. Each report config picks a trigger quantity |
| Events | A1 serving better than threshold, A2 serving worse than threshold, A3 neighbour better than the special cell by an offset, A4 neighbour better than threshold, A5 special cell worse than threshold 1 and neighbour better than threshold 2, A6 neighbour better than a secondary cell by an offset. B1 and B2 are the inter-RAT counterparts of A4 and A5. Each event has an entering and a leaving condition with hysteresis, and must hold for the time-to-trigger. Exact expressions: TS 38.331 |
| Time-to-trigger and hysteresis | Hysteresis widens the gap between entering and leaving, TTT requires the condition to hold continuously. Both reduce ping-pong and add delay. Field names in the ASN.1: `timeToTrigger`, `hysteresis`, `a3-Offset`, `reportInterval`, `reportAmount`, `maxReportCells`. Check the allowed value sets and step sizes in the current ASN.1 |
| L1 and L3 filtering | L1 filtering is physical-layer averaging of samples inside the measurement period (implementation dependent, bounded by the requirements in TS 38.133). L3 filtering is a configured first-order recursive filter applied by RRC, controlled by a filter coefficient per quantity (`filterCoefficientRSRP` and similar). Coefficient 0 means no L3 filtering. The mapping from coefficient to the weight is in TS 38.331 |
| SSB | The SS/PBCH block carries PSS, SSS and PBCH with DM-RS. SSBs are sent in bursts within a 5 ms half frame, periodicity set by the network (UE assumes a default for initial access). The UE measures SSBs inside the SMTC window (`smtc1`, `smtc2`). The number of candidate SSB positions depends on frequency range |
| Quantities | SS-RSRP is a linear power average over the resource elements that carry the secondary synchronisation signal (the PBCH DM-RS may also be used). SS-RSRQ relates SS-RSRP to the carrier RSSI over the measured symbols and bandwidth. SS-SINR relates SS-RSRP to interference plus noise. Definitions are in TS 38.215; do not equate them with LTE definitions |
| Handover | Network sends RRCReconfiguration with `reconfigurationWithSync`; the UE starts a supervision timer, synchronises to the target, performs random access (or RACH-less where configured) and returns RRCReconfigurationComplete. Xn-based and NG-based preparation exist, see TS 38.300 |
| Conditional handover | The target configuration is delivered in advance with an execution condition (conditional events built on A3, A4, A5 and later additions). When the condition holds the UE executes the handover on its own. Several candidates can be prepared. Benefit: the reconfiguration no longer has to cross a degrading link. Cost: resource reservation in candidates |
| Release 18 and 19 mobility | Release 18 added L1/L2 triggered mobility (LTM) within one CU, where a MAC CE triggers a cell switch to a pre-configured candidate using L1 measurement reports. Release 19 work covers inter-CU LTM and conditional LTM, per RAN2 status documents found through web search; confirm in the frozen specifications |
| Beam management | Procedures of beam sweeping, beam refinement at the gNB and UE side, beam indication through TCI states, beam failure detection and recovery. L1-RSRP reporting uses SSB or CSI-RS resources, indicated by SSBRI or CRI. Details: references/beam-management-ssb.md |
| Channel models | TR 38.901 defines large scale parameters, path loss and LOS probability for UMa, UMi street canyon, RMa, InH office and InF, plus small scale models (clustered delay line CDL and tapped delay line TDL). Frequency range of validity and optional features (spatial consistency, blockage, O2I loss) depend on the version. Details: references/channel-models-38901.md |

## 3. Workflow

1. Establish the question type first: explain a concept, tune parameters, interpret simulation output, or check a configuration against the standard. Ask for the spec release, frequency range, deployment scenario and UE speed when they matter.
2. Look up the exact definition in the spec before quoting formulas, value ranges or clause numbers. If the spec cannot be fetched, state that, describe the behaviour in words, and tell the reader which spec to check.
3. Separate the layers of the problem: measurement (filtering, periods), reporting (event, hysteresis, TTT), decision (network algorithm), execution (preparation, random access, interruption), and failure handling (RLF, re-establishment).
4. Map each standard parameter to the simulator parameter that implements it and note where the simulator simplifies (for example, no L1 sampling or no SMTC gaps). See references/measurement-events.md.
5. For simulation results, check the setup before the conclusions: mobility model and speed, channel model and its validity range, beam model, number of UEs, measurement period, and random seeds.
6. Report metrics with definitions: handover rate per UE per time, radio link failures, ping-pong rate with its time threshold, handover failures by type, interruption time, and throughput or SINR around the handover.
7. State assumptions and what was not verified, and keep numbers in the units used by the spec (dBm, dB, ms).

## 4. Decision Rules

- If the question is about a specific field, value range or timer, read the current TS 38.331 ASN.1 and procedure text; if only a summary is available, say so.
- If a user asks why handovers fail, classify first: too late (RLF before or during the command), too early (RLF soon after arriving at the target, back to the source), wrong cell (RLF at the target and re-establishment in a third cell), or preparation failure. Then adjust parameters toward the dominant class. Definitions follow the mobility robustness optimisation text in TS 38.300.
- If ping-pong dominates, raise TTT, hysteresis or L3 filter coefficient (or the A3 offset); if too-late failures dominate, lower them. State that this is a trade-off, not a free improvement.
- If the study compares fixed-parameter A3 against a new algorithm, give both the same measurement chain (same filtering, same measurement period, same reporting interval), or the comparison is not valid.
- If UE speed is high (for example more than 100 km/h), expect measurement staleness: short TTT and light filtering react faster but increase noise-driven triggering, so evaluate several speeds.
- If the scenario is FR2 or uses beamforming, make clear whether the measured quantity is per beam or per cell. Cell quality is derived from the best beams above a threshold, with an optional average; the settings are `nrofSS-BlocksToAverage` and `absThreshSS-BlocksConsolidation` in the ASN.1.
- If CHO is evaluated, specify the execution condition, the number of prepared candidates, the preparation trigger (separate from the execution trigger), and whether candidate resources are reserved; omitting any of these makes results non-reproducible.
- If a simulator offers a simplified handover (instant switch, no random access), say that interruption time is then an input, not a result.
- If channel realism matters (blockage, O2I, spatial consistency), check that the TR 38.901 version and options in use support the frequency and scenario.
- If asked for 6G or Release 20 behaviour, say that 6G studies are not frozen specifications and avoid presenting study items as standard.

## 5. Coding Standards

This skill does not write simulator code. These conventions apply to the equations, configs and analysis scripts that accompany a mobility study.
- Use the spec names for parameters (`timeToTrigger`, `a3-Offset`, `hysteresis`) in config files and code comments, and record the unit and step size next to each value.
- Keep dB and linear quantities distinct in variable names (`rsrp_dbm`, `rsrp_mw`). Average power in the linear domain, filter and compare in the domain the spec specifies, and state which one the code uses.
- Never add dB values that are really power ratios of different quantities (dBm plus dB is fine, dBm plus dBm is not).
- Express time in milliseconds or seconds with one convention per project, and keep the simulation time step explicit; a time step coarser than the TTT or the measurement period invalidates timing results.
- Name events with the spec letters (A3, B1) and keep entering and leaving conditions in separate functions.
- Configure a run from one file (YAML or JSON) that stores the seed, the channel model options and the spec release assumed.
- Do not hard-code spec constants from memory in code; copy them from the spec with a comment that names the spec and its version.

## 6. Project Structure

A layout for a mobility study that is simulator-agnostic:

```text
mobility-study/
  README.md              # question, spec releases assumed, how to rerun
  configs/
    scenario.yaml        # layout, ISD, carrier, bandwidth, SCS, UE speed
    mobility.yaml        # A3 offset, hysteresis, TTT, filter coefficient, CHO conditions
    channel.yaml         # TR 38.901 scenario, options, seed policy
  sim/                   # simulator glue (see ns3-expert or matlab-expert)
  analysis/
    events.py            # extract HO, RLF, ping-pong from logs
    plots.py
  results/               # raw logs, never edited by hand
  notes/
    spec-mapping.md      # table: spec parameter -> simulator parameter -> simplification
```

- Keep a spec-mapping note: for each standard parameter, the simulator parameter that implements it, the value used, and any simplification.
- Store raw event logs (time, UE, serving cell, target cell, event, outcome) so metrics can be recomputed with another ping-pong threshold.
- Keep one config per experiment and commit it with the results.

## 7. Design Patterns

- **Measurement chain as a pipeline**: raw per-beam sample, then L1 averaging, then beam consolidation to a cell value, then L3 filter, then event evaluation. Implement each stage separately so ablations are possible.
- **Event state machine**: per UE, per measurement identity, per neighbour: idle, condition true since time t, reported, leaving. Entering needs the condition to hold for TTT; leaving uses the leaving condition with hysteresis. Cost: state per cell pair.
- **Failure classifier**: a post-processing pass over the event log that labels each handover as success, too late, too early, wrong cell or ping-pong, with the thresholds as parameters.
- **Parameter sweep over a grid**: A3 offset by TTT by speed, with several seeds per point; plot failure and ping-pong surfaces, not single points.
- **Scenario triple**: always give layout (ISD, height), channel scenario (UMa, UMi, ...) and mobility model together, since results transfer poorly across them.
- **Baseline plus variant**: keep a fixed-parameter A3 baseline in every study, and report the variant against it using identical measurement chains.

## 8. Best Practices

- Define every metric in the study: handover rate, ping-pong (handover back to the previous cell within a stated time), radio link failure rate, interruption time, time in outage, and throughput during a window around the handover.
- Report the full parameter set (offset, hysteresis, TTT, filter coefficient, measurement period, reporting interval, and event type) with units.
- Keep the measurement and reporting periods consistent with DRX and SMTC settings; the UE cannot measure faster than its configuration allows (requirements in TS 38.133).
- Use realistic UE speeds and trajectories for the claimed use case (pedestrian, vehicular, rail, UAV), and show at least three speeds.
- Use warm-up time before collecting statistics, so filters and queues have settled.
- Separate cell-edge UEs from all UEs in KPIs; mobility problems concentrate near edges.
- Cross-check one run against an analytical expectation (for example, handover rate approx. crossing rate of cell boundaries) before trusting a sweep.
- When comparing with literature, match the 3GPP release, band, ISD and mobility model, or state the mismatch.
- When using machine learning for handover, keep the standard-compliant signalling in place (the UE still follows the configured events) and state what the learned part controls.

## 9. Performance

- Mobility simulations scale with number of UEs times number of cells times time steps. Compute neighbour measurements only for cells above a distance cut-off; document the cut-off.
- The channel dominates cost: a full TR 38.901 channel with many clusters and antenna elements per UE-cell pair is expensive. Update the channel at a coarser interval than the measurement period only if the coherence time allows (Doppler shift is speed times carrier frequency divided by the speed of light).
- Use independent seeds and run in parallel across seeds, not inside one run.
- For long trajectories, log events, not every sample; keep raw samples only for a few UEs for debugging.
- Pre-compute static terms (path loss between fixed nodes) and cache them.
- For large sweeps, start with a coarse grid and refine around the optimum.

## 10. Security

- Access stratum security (integrity and ciphering of RRC and user plane) is re-keyed on handover; a study that ignores security cost underestimates interruption only slightly, but must say so.
- Measurement reports are integrity protected after security activation; spoofed or injected reports are outside the usual simulation model. If a study addresses fake base stations or measurement manipulation, name the threat model explicitly.
- Research datasets with real UE traces (drive tests, operator logs) can contain identifiers (cell IDs, IMSI-derived values, location). Anonymise before sharing and check licence and consent.
- Do not publish operator-confidential parameter values; use ranges.
- Keep credentials for dataset or simulator services out of repositories and configs.

## 11. Testing

- Unit-test the event logic with synthetic traces: a step change in neighbour power must trigger exactly one report after TTT, a brief spike shorter than TTT must not, and a value inside the hysteresis band must not toggle the state.
- Test the filter: a constant input stays constant, a step converges monotonically, coefficient 0 passes input unchanged.
- Test the failure classifier on hand-built timelines for each failure type.
- Reproduce a known result (for example, ping-pong versus TTT from a published study) before running new scenarios.
- Fix seeds for regression tests and assert metrics within a tolerance, not equal.
- Test unit handling: a dBm to mW round trip and a dB offset addition.
- Check that doubling the TTT never increases the number of triggered events for the same input trace (monotonicity sanity check).

## 12. Review Checklist

- [ ] Spec numbers and release are stated, and clause or table numbers appear only if the text was read.
- [ ] Every mobility parameter has a value, a unit and a source (spec field name).
- [ ] The measurement chain (L1, beam consolidation, L3) is described and identical across compared schemes.
- [ ] Handover failure types and ping-pong have explicit definitions with thresholds.
- [ ] The channel model scenario, frequency range and options are inside the validity range of TR 38.901 for the version used.
- [ ] Speed, trajectory and layout are specified; several speeds are evaluated.
- [ ] Simplifications in the simulator (interruption time, no RACH, no gaps) are listed.
- [ ] Results use several seeds and report spread (see statistics-expert for the tests).
- [ ] Release 18 and later features (CHO variants, LTM) are marked with the release that introduced them.
- [ ] Claims about 6G are marked as study items.

## 13. Production Notes

- Real networks tune mobility through vendor-specific self-optimisation on top of the standard parameters; published default values from papers are rarely deployed values.
- A UE reports based on its configuration; network-side decisions (admission, load balancing, handover target selection) are not specified in detail by 3GPP, so any algorithm statement is a modelling choice.
- Measurement gaps, DRX and UE capability limit how many cells and frequencies are measured; vendor and band combinations differ.
- Drive-test data show effects absent from standard channel models (foliage, bridges, vehicle penetration); say when a simulated result is not validated against measurements.
- Specifications are updated every release and corrected within a release. Record the version of every spec used and re-check parameter value ranges when upgrading.
- In deployment-oriented work, check that the chosen offset and TTT values are permitted by the ASN.1 value set; many continuous values used in simulation are not signallable.
- Handover interruption times quoted for NR depend on the procedure (conventional, DAPS, RACH-less, LTM) and numerology; quote the procedure with the number.

## 14. Examples

A simplified event-A3 evaluator with an L3-style filter for a single UE and one neighbour. It leaves out cell and frequency specific offsets, so it illustrates timing logic only. Confirm the exact entering and leaving expressions in TS 38.331 before using it in a study. The filter weight `alpha` is given directly; the mapping from the configured filter coefficient to the weight is in TS 38.331.

```python
import numpy as np


def l3_filter(samples_dbm: np.ndarray, alpha: float) -> np.ndarray:
    """First-order recursive filter; alpha=1 means no filtering."""
    out = np.empty_like(samples_dbm, dtype=float)
    out[0] = samples_dbm[0]
    for i in range(1, len(samples_dbm)):
        out[i] = (1.0 - alpha) * out[i - 1] + alpha * samples_dbm[i]
    return out


def a3_reports(serving, neighbour, t_ms, offset_db, hys_db, ttt_ms):
    """Return the times (ms) at which an A3-style report would be sent.

    Simplified: no per-cell or per-frequency offsets. The condition must hold
    continuously for ttt_ms; the leaving condition resets the timer.
    """
    reports, since, reported = [], None, False
    for t, s, n in zip(t_ms, serving, neighbour):
        entering = n - hys_db > s + offset_db
        leaving = n + hys_db < s + offset_db
        if entering and not reported:
            since = t if since is None else since
            if t - since >= ttt_ms:
                reports.append(t)
                reported = True
        elif leaving:
            since, reported = None, False
        elif not entering and not reported:
            since = None
    return reports


rng = np.random.default_rng(1)
t = np.arange(0, 4000, 40)                  # one sample per 40 ms
serving = -90 - 0.01 * t + rng.normal(0, 2, t.size)
neighbour = -100 + 0.01 * t + rng.normal(0, 2, t.size)
s_f = l3_filter(serving, alpha=0.5)
n_f = l3_filter(neighbour, alpha=0.5)
print(a3_reports(s_f, n_f, t, offset_db=3.0, hys_db=1.0, ttt_ms=160))
```

A handover log record that supports re-computing metrics later (CSV header):

```text
time_s,ue_id,event,source_cell,target_cell,outcome,rsrp_src_dbm,rsrp_tgt_dbm
```

Spec-mapping note row (markdown), kept in `notes/spec-mapping.md`:

```text
| Spec parameter | Simulator parameter | Value | Simplification |
| a3-Offset      | (simulator name)    | 3 dB  | no cell-specific offsets |
```

## 15. Common Mistakes

- **Citing clause numbers from memory**: clause numbers change between versions. Cite only text that was read, otherwise name the spec.
- **Quoting LTE defaults for NR**: measurement definitions, SSB structure and value sets differ. Use TS 38.215 and TS 38.331.
- **Averaging RSRP in dB when the spec averages power**: linear-domain averaging gives different results at low SINR. State the domain.
- **Treating A3 as a pure offset comparison**: hysteresis, TTT, filtering and the reporting interval together set the actual handover point.
- **Ignoring the leaving condition**: without it, simulated events retrigger on every sample.
- **Counting ping-pong without a time threshold**: any back-and-forth within an unspecified window is not comparable across papers.
- **Comparing schemes with different measurement chains**: changes in filtering can explain the entire gain.
- **Using a channel model outside its validity range**: for example, a scenario defined for a band range other than the one simulated, or a model without spatial consistency for moving UEs in beamformed links.
- **Mixing cell quality and beam quality**: in FR2 the best beam may change faster than the cell quality.
- **Reporting only averages**: handover failures are rare events; show distributions and confidence information (see statistics-expert).
- **Assuming CHO has no cost**: it needs resources in candidate cells and has its own failure modes (condition never met, stale configuration).
- **Calling Release 20 or 6G study results standardised**: they are study items until specified.
- **Confusing Xn and NG handover with the radio procedure**: both end in the same RRC reconfiguration at the UE but differ in core-network involvement and delay.

## 16. References

- [references/measurement-events.md](references/measurement-events.md): measurement configuration structure, events A1 to A6 and B1 B2 in words, hysteresis and TTT behaviour, L1 and L3 filtering, quantity definitions and parameter-to-simulator mapping.
- [references/handover-cho.md](references/handover-cho.md): RRC states, conventional handover phases, RLF handling, failure types, conditional handover, DAPS, LTM, metrics and parameter tuning.
- [references/beam-management-ssb.md](references/beam-management-ssb.md): SSB structure and timing, SMTC, CSI-RS, beam sweeping, TCI, beam failure recovery, cell quality from beams, FR1 and FR2 differences.
- [references/channel-models-38901.md](references/channel-models-38901.md): TR 38.901 scenarios, large scale and small scale models, CDL and TDL, options, validity limits and simulation advice.
- 3GPP specifications portal: https://www.3gpp.org/specifications-technologies and the archive https://www.3gpp.org/ftp/Specs/archive/
- ETSI copies of the specs: https://www.etsi.org/standards (search for TS 138 331 and similar).
- Specs by number: TS 38.300 (NR overall description), TS 38.331 (RRC), TS 38.133 (RRM requirements), TS 38.215 (physical layer measurements), TS 38.304 (idle and inactive UE procedures), TR 38.901 (channel model).
