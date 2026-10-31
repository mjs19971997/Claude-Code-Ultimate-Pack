# TR 38.901 Channel Models

What TR 38.901 specifies for link-level and system-level studies, how its parts fit together, which options matter for mobility simulation, and the mistakes that make results hard to compare. The document was not fetched for this skill, so no path loss coefficients, parameter tables or clause numbers are given here. Read the current version of TR 38.901 for every number, and record its version in the study.

## Contents

1. [What the report covers](#1-what-the-report-covers)
2. [Deployment scenarios](#2-deployment-scenarios)
3. [Large scale model](#3-large-scale-model)
4. [Small scale model](#4-small-scale-model)
5. [Simplified models CDL and TDL](#5-simplified-models-cdl-and-tdl)
6. [Optional features](#6-optional-features)
7. [Antenna models](#7-antenna-models)
8. [Mobility specific advice](#8-mobility-specific-advice)
9. [Reporting checklist](#9-reporting-checklist)

## 1. What the report covers

- TR 38.901 is the channel model for frequencies from 0.5 GHz up to 100 GHz in its recent versions (the validity range changed between versions; check the scope of the version you use).
- It provides a geometry-based stochastic model: large scale parameters (path loss, shadow fading, delay spread, angular spreads, K-factor), cluster generation (delays, powers, angles), and per-ray coefficients with polarisation and Doppler.
- It is used for system-level mobility studies (many cells and users, path loss and shadowing dominate) and for link-level studies (full small-scale fading on a link).
- For handover studies, the large scale part usually matters more than the fast fading: it sets the measured RSRP and thereby the event timing. Fast fading matters when beamforming, SINR-to-BLER mapping and short measurement averaging are modelled.
- The report is a stage of the 3GPP evaluation methodology; the system-level assumptions (layouts, antenna configurations, traffic) are separate documents. Check which methodology (for example, TR 38.802, TR 38.913) the study follows.

## 2. Deployment scenarios

| Scenario | Short description | Typical mobility use |
|---|---|---|
| UMa | Urban macro: base stations above rooftops, hexagonal layout | Vehicular and pedestrian handover studies |
| UMi street canyon | Urban micro: base stations below rooftops in streets | Dense small cells, FR2 mobility |
| RMa | Rural macro: large cells, high speeds | High-speed handover |
| InH | Indoor hotspot (office and mixed office) | Short range indoor mobility |
| InF | Indoor factory with several clutter types | Industrial mobility |
| O2I | Outdoor to indoor penetration as an add-on to outdoor scenarios | Users inside buildings served from outside |

- Each scenario has separate formulas for LOS and NLOS path loss, LOS probability, and large scale parameter statistics. The base station height, UE height and distance ranges are scenario parameters; stay within the ranges given in the document.
- Newer versions add scenarios and extensions (for example, additional factory classes, and variants for non-terrestrial or sidelink use are handled in other reports). Check the table of scenarios in the version you use.
- Hexagonal layouts with wrap-around and a defined inter-site distance are the usual way to build the cell grid. Cell layout and ISD are not part of the channel model itself; they come from the evaluation methodology.

## 3. Large scale model

Components, each defined per scenario in the report:

1. LOS probability as a function of 2D distance (and UE height in some scenarios). Draw LOS or NLOS per link at the start and keep it fixed unless spatial consistency is used.
2. Path loss: a distance-dependent formula with different breakpoints and slopes in LOS and NLOS, and a carrier frequency term. NLOS path loss is bounded below by the LOS value in the scenarios that define it.
3. Shadow fading: log-normal with a scenario and LOS/NLOS specific standard deviation, and a spatial correlation distance. Correlated shadowing along the UE track is essential for realistic handover timing.
4. Other large scale parameters: delay spread, angular spreads, K-factor, with cross-correlations between them. These feed small-scale generation.
5. Penetration loss for O2I (low-loss and high-loss building models), with an additional indoor loss term depending on distance inside.
6. Optional atmospheric and blockage losses, mostly relevant above 6 GHz.

Notes:

- RSRP in a simulation is the transmit power per resource element, plus antenna gains, minus path loss, minus shadow fading, and with fast fading averaged out (or not) by L1 averaging. Document which terms are in.
- Shadow fading must be spatially and temporally consistent for a moving UE. Draw it from a correlated field or a correlated process along the track with the document's correlation distance. Independent samples at each time step produce unrealistic handover counts.
- Correlation between shadowing from different base stations to the same UE is defined in the system-level methodology; ignoring it affects A3 triggers since the comparison involves two cells.
- Use the standard's frequency dependence; copying coefficients from a different carrier is a common error.

## 4. Small scale model

Procedure in the document (steps are described in the report; names below are mine):

1. Set scenario, positions, LOS state, antenna arrays and orientations.
2. Generate large scale parameters with their correlation.
3. Generate cluster delays and powers, then angles of arrival and departure per cluster with random offsets.
4. Draw random phases, cross-polarisation power ratios, and combine rays into channel coefficients with array response and Doppler terms.
5. Optionally scale for UE speed, blockage and spatial consistency.

Points:

- Clusters have sub-clusters for the strongest ones to model delay spread inside a cluster.
- Doppler shift per ray follows the UE velocity vector and the ray's arrival direction, so the channel varies on the scale of the coherence time; this is the key difference between a time-varying model and a Jakes process on a tapped delay line.
- The number of clusters and rays is scenario dependent. A faithful implementation is computationally heavy; see the performance notes in SKILL.md.
- The full model gives frequency-selective channels with spatial structure; with massive MIMO and beamforming it is needed to compute beam gains instead of assuming them.

## 5. Simplified models CDL and TDL

- Clustered delay line (CDL) models A to E: a fixed set of clusters with specified delays, powers and angles, scalable in delay spread. A, B, C are NLOS, D and E are LOS. They support multi-antenna link simulation.
- Tapped delay line (TDL) models A to E: delay profiles without angles, for single-antenna or correlation-matrix based studies. A, B, C are NLOS, D and E are LOS (with a K-factor).
- Both are scaled by a desired RMS delay spread. The document gives a table of example delay spreads for different environments; choose one that matches the scenario and carrier.
- Doppler is set by the UE speed and carrier; specify both.
- Use CDL and TDL for link-level performance (BLER curves, beam tracking) and the full geometry model for system-level mobility.
- A TDL with Jakes Doppler does not carry spatial consistency or beam-dependent behaviour, so avoid it for beam-level mobility analysis.

## 6. Optional features

| Feature | What it adds | Why it matters for mobility |
|---|---|---|
| Spatial consistency | Smooth change of channel and large scale parameters with UE position | Without it, a moving UE sees independent channels at each update; beam tracking and handover timing become unrealistic |
| Blockage model | Additional attenuation from moving blockers (self-blocking and dynamic blockers) | Major cause of beam failure and RLF at FR2 |
| Oxygen absorption | Frequency-dependent atmospheric loss | Matters around 60 GHz |
| Near-field and spatial non-stationarity (check the version) | Distance dependent angle across large arrays | Large-array and short-range studies |
| O2I penetration | Building entry loss, car penetration in some versions | Indoor users served from outside |

- Each option is defined with parameters in the report; read the current version for how each should be switched on and which range of frequencies it supports.
- If the simulator lacks an option, list it in the limitations of the study.
- The default model (without these options) treats each time step as independent in the small-scale part unless the simulator implements the time evolution.

## 7. Antenna models

- The report defines a base antenna element pattern (a 3D element with vertical and horizontal cuts and a maximum gain), polarisation models, and array configurations (rows, columns, polarisations, spacing).
- UE antennas are often modelled as omni elements with small gain, or as arrays at FR2.
- Antenna element pattern, array size and downtilt must match between the channel generation and the beamforming codebook used by the simulator.
- Antenna gain is a separate term from path loss in the link budget; ensure it is not counted twice (for example if the pattern is built into both the channel and the link budget).
- The polarisation slant angle and array orientation are parameters; set them explicitly.

## 8. Mobility specific advice

- State the scenario (UMa, UMi, RMa, InH, InF), the carrier frequency, the bandwidth, the UE height and speed, and the O2I fraction of users.
- For handover studies with many cells, drop UEs into the layout, generate large scale parameters once per link, and evolve shadowing along the track with the correlation distance.
- Compute path loss to every cell each step (or each measurement period), then add antenna gain. Use a cut-off distance for far cells and document it.
- Calibrate the simulation before the study: compare the distributions of coupling loss, wideband SINR and geometry with published calibration results of 3GPP evaluations for the same scenario.
- Check LOS probability behaviour as the UE moves: whether the LOS state flips abruptly or is spatially consistent changes the number of handover triggers near corners.
- High speed (rail, highway) scenarios use specific models in other 3GPP documents (high-speed train); do not assume TR 38.901 RMa covers them. Check the spec scope.
- If you need a non-terrestrial or sidelink channel, use the appropriate report (TR 38.811 and TR 38.821 for non-terrestrial). Check that these are the intended ones.

## 9. Reporting checklist

- [ ] TR 38.901 version and scenario names stated.
- [ ] Carrier frequency, bandwidth, ISD, base station and UE heights, UE speed distribution.
- [ ] Which options are enabled (spatial consistency, blockage, O2I, oxygen absorption).
- [ ] Large scale parameters: how shadowing is correlated in space and time; fast fading on or off; how it enters RSRP.
- [ ] Antenna models and beamforming codebook at both ends.
- [ ] Update interval of the channel and the measurement period.
- [ ] Number of drops, seeds and simulated time per drop.
- [ ] Calibration reference used before the study.
