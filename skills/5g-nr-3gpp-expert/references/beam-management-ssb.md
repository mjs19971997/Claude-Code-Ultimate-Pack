# Beam Management, SSB and CSI-RS

How NR uses SS/PBCH blocks and CSI-RS for synchronisation, mobility measurements and beam management, and how beam-level results relate to the cell-level quantities used by handover events. Values and definitions are described from general knowledge; the exact numbers are in TS 38.211, TS 38.213, TS 38.214, TS 38.215, TS 38.300, TS 38.331 and TS 38.133, none of which were fetched for this skill, so no clause numbers are given. Check the current versions before quoting any number below.

## Contents

1. [Frequency ranges and numerology](#1-frequency-ranges-and-numerology)
2. [SS/PBCH block](#2-sspbch-block)
3. [From beams to cell quality](#3-from-beams-to-cell-quality)
4. [SMTC and measurement timing](#4-smtc-and-measurement-timing)
5. [CSI-RS for mobility and beam management](#5-csi-rs-for-mobility-and-beam-management)
6. [Beam management procedures](#6-beam-management-procedures)
7. [Beam failure detection and recovery](#7-beam-failure-detection-and-recovery)
8. [Beams and handover](#8-beams-and-handover)
9. [Modelling advice](#9-modelling-advice)
10. [Quick reference](#10-quick-reference)

## 1. Frequency ranges and numerology

- FR1 covers sub-7 GHz bands (the range is stated as 410 MHz to 7.125 GHz in recent releases). FR2-1 covers bands in the 24 to 52 GHz region, and FR2-2 extends to 71 GHz. Check the exact edges in TS 38.104 or TS 38.300 for the release you use.
- Subcarrier spacing for data in FR1: 15, 30 and 60 kHz. FR2: 60 and 120 kHz, with higher values (480 and 960 kHz) for the upper FR2-2 range. Not every spacing is permitted for every band.
- SSB uses its own spacing set: 15 or 30 kHz in FR1, 120 or 240 kHz in FR2-1, with extensions in FR2-2. Each band lists the permitted SSB pattern (cases A to E, and others in newer releases) in TS 38.101.
- Higher frequency means higher path loss and larger Doppler shift for the same speed; beamforming gain compensates, and beams become narrow, which increases mobility problems (blockage, beam misalignment).

## 2. SS/PBCH block

- An SSB spans four OFDM symbols and 20 resource blocks. It carries PSS, SSS and PBCH (with its DM-RS). The UE uses it for cell search, time and frequency synchronisation, reading the master information block, and cell quality measurement.
- SSBs are grouped in an SS burst set that occupies a 5 ms half frame, repeated with a period chosen by the network. The configured periodicity values run from 5 ms to 160 ms. For initial access the UE assumes a default periodicity (20 ms).
- The maximum number of SSB positions in a burst set depends on the frequency: 4 below about 3 GHz, 8 between about 3 and 6 GHz, and 64 at FR2. Each position can carry an SSB transmitted in a different beam, so one gNB sweeps through many beams per burst set.
- The SSB index (and the half frame bit) is conveyed by the PBCH DM-RS and the PBCH payload, so a UE can tell which beam it hears.
- Actually transmitted SSB positions are signalled (`ssb-PositionsInBurst`). A simulator should send only these, not all candidate positions.
- Cell-defining SSBs sit on the synchronisation raster; non-cell-defining SSBs exist for measurement purposes on other positions. Check the details if you model multi-SSB carriers.

## 3. From beams to cell quality

A cell has several SSB beams. The UE derives the cell quality used for events in a defined way:

1. Measure each detected SSB beam (per-beam L1 results).
2. Select the best beam value.
3. Optionally average the best beams whose value is above an absolute threshold, up to a configured number of beams (`nrofSS-BlocksToAverage`, threshold `absThreshSS-BlocksConsolidation`). If none is above the threshold, the cell quality is the best beam value. The consolidation rule is in TS 38.331 (field names from memory, check them).
4. Apply the L3 filter to the cell-level result.

Implications:

- With a single-beam model (or one wide beam per cell), cell quality equals beam quality, and handover behaviour depends only on path loss and shadowing.
- With narrow beams, the best beam switches often at FR2, and beam-level gain and misalignment dominate the cell value near the cell edge.
- Averaging more beams smooths the cell quality but lowers sensitivity to the best direction.
- The beam used for reporting (SSB index) can also be reported, so the target can pick a beam for the first transmissions (random access occasions map to SSB indices).

## 4. SMTC and measurement timing

- The SS/PBCH block measurement timing configuration (SMTC) tells the UE the periodicity, offset and duration (window length in ms) of the window in which neighbour SSBs are transmitted. A second configuration (`smtc2`) may serve lists of cells with different periodicity.
- The UE measures only inside the window. A short window with a long period reduces UE power consumption, but gives fewer samples and slower reaction.
- `ssb-ToMeasure` indicates which SSB positions the UE should measure; leaving positions unmeasured speeds up the measurement.
- Measurement accuracy and evaluation period are specified in TS 38.133 as functions of SMTC period, DRX and frequency range. For performance claims, read the requirements from the current text.
- If the SSB periodicity of the network is 20 ms and the UE sees every burst, a simulator can sample at that rate; if neighbours use 40 ms or 80 ms, sample at that rate.

## 5. CSI-RS for mobility and beam management

- CSI-RS is configured per resource (periodic, semi-persistent or aperiodic) and carries its own port, density and bandwidth. Unlike SSB, it is UE-specific or group-specific and can be narrower and denser.
- For mobility, a measurement object can use CSI-RS resources, so cell quality derives from CSI-RS instead of SSB. This helps when SSB beams are wide and the network wants finer beams, at the cost of configuration signalling and overhead.
- For beam management, CSI-RS resource sets are used for beam refinement and for tracking. Reports (L1-RSRP or L1-SINR) return the best resource indices (CRI) or SSB indices (SSBRI) with their quality.
- CSI-RS can be used for L1/L2 triggered mobility reports of candidate cells; the Release 19 discussions reportedly added CSI-RS alongside SSB for that (web search summary; verify).
- CSI-RS based RSRP definition: same idea as SS-RSRP but over CSI-RS resource elements, per TS 38.215.
- Resource overhead of CSI-RS grows with the number of beams measured; count it when comparing beam schemes.

## 6. Beam management procedures

Beam management is usually described as three procedures (from the NR study documents and TS 38.300 overview):

| Procedure | Purpose | What happens |
|---|---|---|
| P-1 | Initial beam selection | The gNB sweeps Tx beams (SSB or CSI-RS); the UE measures and reports the best |
| P-2 | Tx beam refinement | The gNB sweeps a finer set of beams around the selected one; the UE reports the best |
| P-3 | Rx beam refinement | The gNB keeps its Tx beam fixed; the UE sweeps its Rx beams (repeated transmission) |

- Beam indication uses transmission configuration indicator (TCI) states. A TCI state names a reference signal (SSB or CSI-RS) with which the target channel is quasi co-located, in terms of Doppler, delay and spatial receive parameter. The gNB updates TCI states through RRC, MAC CE and DCI.
- Unified TCI framework (Release 17 onward) lets one indication apply to multiple channels and signals; check the release notes for features and UE capability.
- Beam reporting is part of CSI reporting (`reportQuantity` of cri-RSRP or ssb-Index-RSRP and related options). Report periodicity and resource counts bound how quickly beams track the UE.
- Typical beam-management cost metrics: reference-signal overhead, reporting overhead, and latency of beam update.
- Multi-panel UE and multi-TRP operation add choices (simultaneous transmission from several panels or TRPs); studies must state them.

## 7. Beam failure detection and recovery

- The UE monitors a set of beam failure detection reference signals (by default those in the active TCI state). When enough consecutive indications show quality below a threshold, it declares beam failure on the cell (counter and timer in `beamFailureRecoveryConfig`, see TS 38.331).
- Recovery: the UE identifies a candidate beam among configured candidate reference signals above a threshold, then sends a recovery request through random access resources tied to that beam (contention-free or contention-based), or via the scheduling request and MAC CE for secondary cells. The gNB answers and updates beams.
- Beam failure is not radio link failure. A successful recovery keeps the connection; unsuccessful recovery can lead to RLF.
- High-speed rotation, blockage and mobility around corners are the main causes at FR2.
- In a study, report the beam failure rate, recovery success rate and recovery time separately from handover results.

## 8. Beams and handover

- A handover command can carry the target SSB or CSI-RS resources and associated random access occasions, so the UE picks the target beam when it performs random access.
- Time between a beam change and cell change is short at FR2; failure to refine beams in the target cell after handover leads to a poor first transmission and a drop in SINR.
- Candidate target selection by the network works from reported cell quality plus optionally the best beams; beam-level reports can improve target choice.
- With CHO or LTM, the target beam used at execution is the one the UE finds best at that moment; for LTM, the L1 report names it.
- Beam changes inside a cell are not handovers and should not be counted as such; keep separate counters.

## 9. Modelling advice

- Decide the beam model before the mobility algorithm: omnidirectional, sectorised antenna pattern, fixed beam codebook, or full beam sweeping. State the number of beams, beamwidth, codebook and gain model.
- Use a codebook that matches the antenna array in the channel model; mixing a TR 38.901 antenna array with a different beam pattern assumption gives inconsistent gains.
- Time-align beam sweeping with the SSB periodicity; a UE cannot see a new beam faster than the burst period.
- Include UE-side beamforming or a UE antenna model for FR2, since receive gain is large.
- Check coverage statistics against known behaviour: median RSRP versus distance should follow the path loss model with the beamforming gain added.
- Keep beam-level logs for a subset of UEs so that misalignment events can be inspected.
- Do not apply FR1 delay and Doppler expectations to FR2 without recomputing them.

## 10. Quick reference

| Item | SSB | CSI-RS |
|---|---|---|
| Purpose | Cell search, synchronisation, cell-level and beam-level measurement | Beam refinement, tracking, CSI, optionally mobility |
| Configuration | Cell-wide; periodicity, positions, SMTC for neighbours | Per UE or group; resource sets with periodic, semi-persistent or aperiodic timing |
| Beam identity | SSB index | CSI-RS resource index (CRI) |
| Quantities | SS-RSRP, SS-RSRQ, SS-SINR | CSI-RSRP, CSI-RSRQ, CSI-SINR, L1-RSRP, L1-SINR |
| Overhead | Fixed by burst structure | Grows with number of configured resources |
| Use in events | Default for A1 to A6 | Selectable in the measurement object |

Common sources of confusion:

- "RSRP" without a prefix is ambiguous: say SS-RSRP, CSI-RSRP or L1-RSRP.
- An SSB index is a beam label within one cell and carrier; the same index in two cells is unrelated.
- Candidate positions (the maximum number of SSBs a band allows) are not the same as transmitted positions.
- L1-RSRP is reported in a different range and step size from L3 RSRP; check TS 38.133 before comparing.
- Beam management reports use CSI-report machinery, so their timing follows CSI report periodicity, not the SMTC.
- Beam sweeping time grows with the number of beams; at 64 beams with 20 ms periodicity, the UE sees each beam once per period at best.
