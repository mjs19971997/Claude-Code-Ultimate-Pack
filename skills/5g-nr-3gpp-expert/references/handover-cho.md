# Handover, Conditional Handover and Failures

RRC states, the phases of a conventional NR handover, radio link failure handling, how failures are classified, conditional handover (CHO) and related Release 16 to 19 mobility features, and the metrics used when tuning. Behaviour is described in words; exact procedures, timers and clause numbers are in TS 38.300 (overall description, mobility) and TS 38.331 (RRC), which were not fetched for this skill. Check them before quoting timer names or values.

## Contents

1. [RRC states and transitions](#1-rrc-states-and-transitions)
2. [Conventional handover phases](#2-conventional-handover-phases)
3. [Radio link failure and re-establishment](#3-radio-link-failure-and-re-establishment)
4. [Failure classification](#4-failure-classification)
5. [Conditional handover](#5-conditional-handover)
6. [Other mobility procedures](#6-other-mobility-procedures)
7. [Release 18 and 19 L1 and L2 triggered mobility](#7-release-18-and-19-l1-and-l2-triggered-mobility)
8. [Metrics](#8-metrics)
9. [Tuning rules of thumb](#9-tuning-rules-of-thumb)

## 1. RRC states and transitions

| State | UE context | Mobility | Typical signalling |
|---|---|---|---|
| RRC_IDLE | Not kept in the RAN | Cell reselection by UE using system information (priorities, thresholds, ranking) per TS 38.304; paging via the core network | RRCSetupRequest, RRCSetup, RRCSetupComplete |
| RRC_INACTIVE | Kept in the RAN and the core; RAN notification area | Cell reselection by UE; RAN-based paging; notification area updates | RRCRelease with suspend configuration, RRCResumeRequest, RRCResume |
| RRC_CONNECTED | Active | Network controlled: measurement reports, handover commands | RRCReconfiguration, measurement report, RRCReestablishment |

- Inactive exists to cut signalling and latency for UEs that stay attached with infrequent data, and is the usual state of low-activity users in simulations that include a state machine.
- Transitions: setup moves IDLE to CONNECTED; release moves CONNECTED to IDLE or INACTIVE (when a suspend configuration is included); resume moves INACTIVE to CONNECTED.
- Studies of handover only involve the CONNECTED state. Studies of idle mobility (reselection) use TS 38.304; do not mix the two vocabularies.
- The idle reselection process ranks cells on measured quality with offsets, applies priorities between frequencies, and uses thresholds to decide when to measure; exact criteria are in TS 38.304.

## 2. Conventional handover phases

1. Measurement. The UE is configured with events (see measurement-events.md) and reports when the entering condition holds for the time-to-trigger.
2. Decision. The source gNB selects a target. The algorithm (offset only, load, mobility prediction, learned policy) is not standardised.
3. Preparation. The source sends a handover request to the target over Xn (or through the core network for NG-based handover). The target performs admission control, reserves resources, and returns the configuration the UE will use. The source then builds the handover command.
4. Execution. The source sends RRCReconfiguration containing `reconfigurationWithSync` (target cell identity, new C-RNTI, random access resources, and so on). The UE starts a supervision timer, detaches from the source, synchronises to the target, and performs random access. It then sends RRCReconfigurationComplete to the target.
5. Completion. The target requests a path switch to the core (Xn case); data forwarding from source to target covers the gap. The source context is released.

Points for analysis:

- Interruption time is the user-plane gap between the last data from the source and the first from the target. Contributors: detach and synchronisation, random access, RRC reconfiguration completion, and the first scheduling at the target. Procedure variants (below) reduce parts of it.
- The command is sent over the source link at the moment it is worst. This is the main reason for too-late failures, and the motivation for CHO.
- Preparation signalling over Xn takes backhaul time; models with zero backhaul delay understate it.
- If the supervision timer expires, the UE treats the handover as failed and starts re-establishment.

## 3. Radio link failure and re-establishment

- The UE monitors the downlink radio link quality of the serving cell with out-of-sync and in-sync indications from the physical layer, based on hypothetical control-channel error rates (thresholds Qout and Qin, defined in TS 38.133).
- After a configured number of consecutive out-of-sync indications the UE starts a timer; if no recovery occurs before expiry, it declares radio link failure (RLF). The counter and timer names (N310, N311, T310, T311) and values are in TS 38.331; check the current text.
- Other RLF causes: random access problem, maximum RLC retransmissions, and beam failure recovery failure.
- After RLF the UE selects a cell and tries RRC re-establishment. Re-establishment succeeds quickly if the selected cell already holds the context (prepared cell); otherwise the UE falls back to idle and a new connection is required.
- Time spent between RLF and a restored connection is outage, not interruption; count the two separately.
- A UE report of the failure (RLF report) can be retrieved by the network and used for mobility robustness optimisation.
- In simulators, check which of these triggers exist. A pure SINR threshold with a timer is a common simplification of the first one.

## 4. Failure classification

Mobility robustness optimisation (MRO) text in TS 38.300 classifies failures from the reports. A practical set for analysis:

| Class | Description | Typical cause |
|---|---|---|
| Too late | RLF occurs before or during handover, and the UE re-establishes in a different cell | Offset, TTT or filter too large; high speed; sharp corner |
| Too early | RLF shortly after a successful handover, or handover failure, and the UE returns to the source cell | Offset too small, TTT too short; target not yet stable |
| Wrong cell | RLF shortly after handover to cell B, and the UE re-establishes in a third cell C | Poor target choice, overlapping coverage, neighbour list problems |
| Preparation failure | Target rejects (no resources) or the command is lost | Load, backhaul loss |
| Ping-pong | Handover A to B followed by B to A within a short time | Fluctuating signals at border, small hysteresis |

- Ping-pong is not a failure in the RLF sense, but a quality problem. Define the time window (for example, one second) explicitly and report it.
- Classification needs the timeline per UE: the time of each handover command, RLF, and the cell of re-establishment. Log them, do not infer afterwards.
- The window that separates "too early" from other classes is a parameter; report it.
- Report the failure rate per UE per hour or per handover, with the denominator stated.

## 5. Conditional handover

Idea: deliver the target configuration early, while the source link is still good, together with a condition. The UE evaluates the condition and executes the handover without further commands.

Sequence:

1. The source decides to prepare one or more candidates (preparation trigger, typically an earlier or looser condition than execution). It sends handover requests with a conditional indication to each candidate.
2. Each candidate admits the UE and returns a configuration. The source packages them in an RRCReconfiguration with the conditional configuration list (`condReconfigToAddModList`, `condRRCReconfig`) and one or more measurement identities that describe the execution condition.
3. The UE keeps the source connection, and evaluates the execution condition on each candidate. It continues to use the source link for data.
4. When a condition holds, the UE applies the stored configuration for that candidate, detaches, and executes random access to the target. After completion the stored configurations of other candidates are released.
5. The target informs the source (and the other candidates), which release the reserved resources and forward data.

Considerations:

- Execution events reuse the A3, A4, A5 logic as conditional events (condEvent names in the ASN.1). Later releases add other condition types (for example time-based or location-based ones for non-terrestrial networks). Check the current TS 38.331 for the list.
- Preparation and execution conditions are separate parameters. A common setup makes the preparation trigger earlier (lower offset) and the execution trigger the conventional one, so that the command no longer depends on a bad link.
- Cost: resources are reserved in every candidate until execution or release, and configurations can become stale if conditions do not hold for a long time. Studies should report the number of prepared cells per UE and reservation time.
- Benefit: fewer too-late failures at high speed, shorter command-related delay. Risks: too-early execution because it triggers without network control; with multiple conditions, which candidate wins is decided by the UE.
- CHO does not remove the random access and synchronisation interruption. Combine it with the variants below to shorten that.
- Variants and extensions exist for the dual connectivity case: conditional PSCell addition and change (CPAC), introduced in Release 17 and extended in later releases (check the release descriptions before using them).

## 6. Other mobility procedures

- DAPS handover (Release 16): the UE keeps the source link while it connects to the target, reducing user-plane interruption for the data radio bearers it is configured for. Costs: UE needs two simultaneous links, and the uplink power may be shared.
- RACH-less handover: where the target configuration allows, the UE skips random access, relying on the timing advance and uplink grant in the command. Applicability depends on the deployment; check the spec text.
- Inter-frequency and inter-RAT handover: use A4, A5, B1 and B2; need gaps. Evaluate the throughput cost of gaps.
- Dual connectivity: SN addition, release and change handle secondary cells, with their own events. Studies of PSCell mobility must state whether the master or secondary node is the anchor.
- Non-terrestrial networks (Release 17 onward): long delays and satellite movement lead to time and distance based conditions; the channel and measurements differ from terrestrial ones. This skill covers only the concepts.
- Integrated access and backhaul and sidelink mobility have separate procedures not covered here.

## 7. Release 18 and 19 L1 and L2 triggered mobility

Information from RAN2 status documents and summaries found by web search; verify against the frozen specifications.

- L1/L2 triggered mobility (LTM) was introduced in Release 18 for mobility within a single central unit. The network pre-configures candidate cell configurations through RRC. The UE sends L1 measurement reports (based on beam measurements of the candidate cells). A MAC control element then triggers the cell switch to a candidate, which avoids a full RRC reconfiguration at the time of the switch.
- The goal is lower interruption time than conventional handover. Performance numbers depend on whether the target is synchronised in advance and whether random access is needed; do not quote numbers without a source.
- Release 19 work covers inter-CU LTM (candidates belong to several gNB-CUs), measurement enhancements including event-triggered L1 measurement reports, and conditional LTM, which combines pre-configuration with a UE-evaluated condition. At the time of writing the Release 19 specifications are described as frozen (December 2025, per web news), with only corrections allowed afterwards.
- For a study of LTM, state the release, the candidate set size, the L1 report configuration, the trigger path (network decision on L1 reports, or UE condition), and the interruption model.
- Release 20 continues 5G-Advanced work in parallel with 6G studies; treat anything beyond Release 19 as in progress.

## 8. Metrics

| Metric | Definition guidance |
|---|---|
| Handover rate | Successful handovers per UE per unit time (or per km), with UE speed stated |
| Handover failure rate | Failed handovers divided by attempts, by class (section 4) |
| RLF rate | RLF events per UE per unit time, separate from handover failure |
| Ping-pong ratio | Handovers returning to the previous cell within a stated window divided by all handovers |
| Interruption time | Gap in user-plane delivery around the handover, in ms, per procedure variant |
| Outage time | Time without a usable connection, including RLF and re-establishment |
| Time of stay | Duration in a cell; useful for detecting short stays |
| SINR / throughput around handover | Mean values in a window before and after the handover, for cell-edge UEs |
| Signalling overhead | Preparation messages and reservation time, important for CHO and LTM |

- Report distributions (percentiles) as well as means; mobility events are bursty.
- Do not compare handover rates across scenarios with different cell sizes unless normalised by distance or boundary crossings.

## 9. Tuning rules of thumb

- Start from the failure mix: lots of too-late failures, reduce offset, TTT or filtering; lots of ping-pong or too-early, increase them.
- At low speed the main risk is ping-pong; at high speed it is too-late failure. A single fixed setting will trade one for the other; speed-dependent scaling is a common research topic.
- Hysteresis and TTT have overlapping effects; sweep them together with the offset instead of one at a time.
- Make the load dimension explicit: low load makes preparation succeed; high load adds preparation failures.
- For CHO, tune the preparation trigger first (so candidates are ready early), then the execution condition.
- Validate every tuned setting at speeds outside the tuning range.
- Cross-check against the signallable value sets in the ASN.1; continuous optimised values must be rounded to allowed values and the study rerun.
