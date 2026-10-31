# The 5G-LENA nr Module

Installing the CTTC `nr` module, the v5.1 scenario structure (NrHelper, operation bands, bandwidth parts, channel, beamforming), QoS flows, traces, and what the module supports for handover. Checked on 2026-10 against the nr `5g-lena-v5.1.y` branch (helper headers, `examples/`, `test/`), its `README.md`, `CHANGES.md` and `RELEASE_NOTES.md`, and the ns-3.49 source. Spec interpretation (numerology tables, TDD patterns, 3GPP procedures) belongs to 5g-nr-3gpp-expert.

## Contents

1. [Versions and compatibility](#1-versions-and-compatibility)
2. [Installing nr](#2-installing-nr)
3. [Scenario skeleton for v5.1](#3-scenario-skeleton-for-v51)
4. [Spectrum, bandwidth parts and numerology](#4-spectrum-bandwidth-parts-and-numerology)
5. [Beamforming and antennas](#5-beamforming-and-antennas)
6. [Schedulers, QoS flows and traffic](#6-schedulers-qos-flows-and-traffic)
7. [Handover](#7-handover)
8. [Traces and statistics](#8-traces-and-statistics)
9. [API drift and common errors](#9-api-drift-and-common-errors)

## 1. Versions and compatibility

nr is developed by CTTC in https://gitlab.com/cttc-lena/nr and is built as an ns-3 contrib module. Each release works with one ns-3 release; mixing them fails at compile time.

| nr release | Branch | ns-3 | Date (GitLab tag / README) |
|---|---|---|---|
| v5.1 | `5g-lena-v5.1.y` | ns-3.48 | 2026-08-06 |
| v5.0 | `5g-lena-v5.0.y` | ns-3.48 | 2026-07 |
| v4.2 | (see compatibility table) | ns-3.47 | 2026-03 |
| v4.1.1 | `5g-lena-v4.1.1` | ns-3.46 | 2025-10 |

- The newest tag at the time of checking was v5.1. The nr `CHANGES.md` on master already has a "v5.1 to v5.2" section, so master is a development line; use a release branch for experiments.
- The newest ns-3 release is 3.49 (2026-10), which is newer than the ns-3.48 that nr v5.1 states as compatible. Check out ns-3.48 for nr v5.1 unless the nr README or release notes list ns-3.49.
- The README of nr contains an install example for an older pair (ns-3.46 with v4.1.1); take the pairing from the compatibility table in the README and the "Supported platforms" section of `RELEASE_NOTES.md`, not from the example commands.
- v5.0 raised the minimum CMake to 3.25.2 to match ns-3.48. Supported platforms listed for v5.0 and v5.1 include Ubuntu 22.04 and 25.10, Arch Linux, and macOS on ARM, with g++ 11, 12, 13 and 15 and clang 11, 14 and 20.
- v5.0 release notes recommend two ns-3 merge requests: !2929 (FDD users: without it some NLOS UEs can receive about 30 dB less power; TDD is unaffected) and !2883 (much faster 3GPP channel computation). Check whether the ns-3 tag in use already contains them.
- nr no longer depends on the upstream ns-3 `lte` module (since v3.2); it carries its own RRC, RLC, PDCP, EPC and X2 code.

## 2. Installing nr

```bash
git clone https://gitlab.com/nsnam/ns-3-dev.git
cd ns-3-dev
git checkout -b ns-3.48 ns-3.48
cd contrib
git clone https://gitlab.com/cttc-lena/nr.git
cd nr
git checkout -b 5g-lena-v5.1.y origin/5g-lena-v5.1.y
cd ../..
./ns3 configure -d default --enable-examples --enable-tests
./ns3 build
./ns3 show targets | grep nr
./ns3 run cttc-nr-demo
```

- nr goes into `contrib/nr`, not `src/`. `git status` in ns-3-dev lists it as untracked; that is expected.
- Optional packages (install before configuring): `libeigen3-dev` (MIMO features), `sqlite3` and `libsqlite3-dev` (SQLite-based traces and realistic beamforming). The configure output should show "Eigen3 support: ON" and "SQLite support: ON"; fix the missing library and re-run configure otherwise.
- The `nr` library target cannot be run; build it with `./ns3 build nr`. Examples are separate targets (`cttc-nr-demo`, `cttc-nr-mimo-demo`, `cttc-nr-cc-bwp-demo`, `cttc-realistic-beamforming`, `lena-lte-comparison` and others in `contrib/nr/examples`).
- Limit the build with `--filter-module-examples-and-tests "nr"` when only nr examples are needed.
- Record the nr commit next to the ns-3 commit for every result (see [reproducible-experiments.md](reproducible-experiments.md)).
- Include with `#include "ns3/nr-module.h"`; plus `antenna`, `buildings` (indoor scenarios), `mobility`, `point-to-point`, `internet`, `applications`, `flow-monitor` modules.

## 3. Scenario skeleton for v5.1

Condensed from `examples/cttc-nr-demo.cc` of the v5.1 branch (single band, one BWP, downlink UDP). Copy the exact code from the example of the release in use; names have changed between releases.

```cpp
// Nodes and positions: GridScenarioHelper or MobilityHelper
NodeContainer gnbNodes, ueNodes;       // created and positioned beforehand

Ptr<NrPointToPointEpcHelper> epc = CreateObject<NrPointToPointEpcHelper>();
Ptr<IdealBeamformingHelper> bf = CreateObject<IdealBeamformingHelper>();
Ptr<NrHelper> nr = CreateObject<NrHelper>();
nr->SetBeamformingHelper(bf);
nr->SetEpcHelper(epc);

// Spectrum: one operation band, one contiguous CC, one BWP spanning it
CcBwpCreator ccBwpCreator;
CcBwpCreator::SimpleOperationBandConf bandConf(28e9, 100e6, 1);   // Hz, Hz, number of CCs
OperationBandInfo band = ccBwpCreator.CreateOperationBandContiguousCc(bandConf);

// Propagation: scenario, condition, model
Ptr<NrChannelHelper> channel = CreateObject<NrChannelHelper>();
channel->ConfigureFactories("UMi", "Default", "ThreeGpp");
channel->SetPathlossAttribute("ShadowingEnabled", BooleanValue(false));
channel->AssignChannelsToBands({band});
BandwidthPartInfoPtrVector allBwps = CcBwpCreator::GetAllBwps({band});

// Beamforming and antennas
bf->SetAttribute("BeamformingMethod", TypeIdValue(DirectPathBeamforming::GetTypeId()));
nr->SetUeAntennaAttribute("NumRows", UintegerValue(2));
nr->SetUeAntennaAttribute("NumColumns", UintegerValue(4));
nr->SetUeAntennaAttribute("AntennaElement", PointerValue(CreateObject<IsotropicAntennaModel>()));
nr->SetGnbAntennaAttribute("NumRows", UintegerValue(4));
nr->SetGnbAntennaAttribute("NumColumns", UintegerValue(8));
nr->SetGnbAntennaAttribute("AntennaElement", PointerValue(CreateObject<IsotropicAntennaModel>()));

// Devices, deterministic streams, per-BWP attributes
NetDeviceContainer gnbDevs = nr->InstallGnbDevice(gnbNodes, allBwps);
NetDeviceContainer ueDevs = nr->InstallUeDevice(ueNodes, allBwps);
nr->AssignStreams({.gnbDevs = gnbDevs, .ueDevs = ueDevs});
NrHelper::GetGnbPhy(gnbDevs.Get(0), 0)->SetAttribute("Numerology", UintegerValue(3));
NrHelper::GetGnbPhy(gnbDevs.Get(0), 0)->SetAttribute("TxPower", DoubleValue(35.0));  // dBm

// Core network, IP and attachment
auto [remoteHost, remoteHostAddr] = epc->SetupRemoteHost("100Gb/s", 2500, Seconds(0.0));
InternetStackHelper internet;
internet.Install(ueNodes);
Ipv4InterfaceContainer ueIfaces = epc->AssignUeIpv4Address(NetDeviceContainer(ueDevs));
nr->AttachToClosestGnb(ueDevs, gnbDevs);
```

- Order matters: create helpers and set helper-level attributes (antennas, scheduler, handover algorithm, BWP manager) before the matching `Install*Device` call; use `NrHelper::GetGnbPhy(dev, bwpIdx)->SetAttribute(...)` for per-BWP changes after installation.
- `AssignStreams` with the parameter struct (designated initialisers, C++20) assigns streams to the scenario, beamforming, devices, UE and gNB internet stacks, remote hosts and optionally the EPC from distinct base offsets. The older form `AssignStreams(NetDeviceContainer, int64_t)` still exists. Call it after the objects exist and before `Simulator::Run()`.
- `SetupRemoteHost(dataRate, mtu, delay)` returns the remote host node and its address; place server or client applications there. Start applications after attachment has completed; the demo starts them at 400 ms.
- UE and gNB positions: use `GridScenarioHelper` (see the demo), `HexagonalGridScenarioHelper` for multi-cell layouts, or `MobilityHelper` with `ListPositionAllocator` and `ConstantPositionMobilityModel` / `ConstantVelocityMobilityModel`. gNB height and UE height matter for 3GPP channel scenarios.
- The scenarios in `NrChannelHelper::Scenario` are `RMa`, `UMa`, `UMi`, `InH` and the InH office variants, `InF`, V2V, NTN variants and `Custom`; `ConfigureFactories` takes them as strings (the demo passes `"UMi"`), so read the header of the release for the accepted spellings. Models: `ThreeGpp`, `TwoRay`, `NYU`, `SionnaRT`. Conditions: `LOS`, `NLOS`, `Buildings`, `Default`.

## 4. Spectrum, bandwidth parts and numerology

- Hierarchy: operation band -> component carriers (CC) -> bandwidth parts (BWP). `SimpleOperationBandConf(centralFrequency, bandwidth, numCc)` builds a band with one BWP per CC. `CcBwpCreator::GetAllBwps({band1, band2})` flattens bands into the vector passed to `InstallGnbDevice` / `InstallUeDevice`.
- Each BWP is a separate PHY and MAC instance with its own numerology, slot pattern and TX power. In `cttc-nr-demo` two bands carry two BWPs with different numerologies (4 and 2), and traffic classes are mapped to BWPs.
- BWP ids are numbered in install order (v4.2 and later) and ARFCNs follow 3GPP numbering. Per-BWP access: `NrHelper::GetGnbPhy(gnbDev, bwpIndex)`, `NrHelper::GetUePhy(ueDev, bwpIndex)`.
- Per-BWP attributes on `NrGnbPhy` include `Numerology` (default 0), `TxPower` (dBm), `Pattern` (slot pattern string; default `"F|F|F|F|F|F|F|F|F|F|"`, all flexible), `CsiRsModel`, `CsiRsPeriodicity`. Check `./ns3 show typeid ns3::NrGnbPhy` for the full list; the meaning of slot types is in 3GPP TS 38.211 (5g-nr-3gpp-expert).
- Split total transmit power across BWPs in proportion to bandwidth, as the demo does, or the comparison between configurations is biased.
- Map traffic to BWPs with `nr->SetGnbBwpManagerAlgorithmAttribute("<5QI name>", UintegerValue(bwpIndex))`; for example `"NGBR_LOW_LAT_EMBB"` and `"GBR_CONV_VOICE"` in the demo.
- v5.0 added same-cell primary BWP switching driven by per-carrier RSRP measurements (`NrUeRrc::BwpSwitchHysteresis`); v5.1 made FDD configuration mostly automatic: the gNB advertises its UL carrier in SIB1 and the UE derives its primary UL BWP, so the manual `PrimaryUlIndex` and `SetOutputLink()` setup of earlier releases is not needed for single DL/UL pair cells.
- The default is TDD-style operation on a single carrier. FDD, inverted UL/DL carrier roles and multi-carrier setups are covered by the examples of the release in use.

## 5. Beamforming and antennas

- Antenna arrays: `SetGnbAntennaAttribute` / `SetUeAntennaAttribute` with `NumRows`, `NumColumns`, `AntennaElement` (`IsotropicAntennaModel` as in the demo, or another antenna element model of the `antenna` module).
- Ideal beamforming: `IdealBeamformingHelper`, attribute `BeamformingMethod` (default `CellScanBeamforming`) and `BeamformingPeriodicity` (default 100 ms; 0 means never updated). Algorithms in `ideal-beamforming-algorithm.h`: `CellScanBeamforming`, `CellScanQuasiOmniBeamforming`, `DirectPathBeamforming`, `QuasiOmniDirectPathBeamforming`, `DirectPathQuasiOmniBeamforming`, `OptimalCovMatrixBeamforming`, `KroneckerBeamforming`, `KroneckerQuasiOmniBeamforming`.
- Realistic beamforming: `RealisticBeamformingHelper` with SRS-based channel estimation and trigger events (see `cttc-realistic-beamforming`; needs SQLite). v5.0 fixed the beam scan and SRS channel-estimation models (receive-side zenith step, time-domain filtering gain); results from earlier releases of these paths are not comparable.
- `DirectPathBeamforming` points beams at the geometric direction and is cheap; cell-scan methods search a codebook and cost much more per update. Use direct path for large scenarios and scan or realistic methods when beam misalignment is the topic.
- Attach the beamforming helper with `nr->SetBeamformingHelper(...)` before installing devices, as the demo does.
- MIMO (precoding matrices, rank, CSI feedback) needs Eigen3 and is shown in `cttc-nr-mimo-demo`; check the release notes of the version in use for supported modes before relying on it.
- Radio environment maps: `rem-example` and `rem-beam-example` in the examples directory produce coverage maps.

## 6. Schedulers, QoS flows and traffic

- Scheduler: `nr->SetSchedulerTypeId(TypeId::LookupByName("ns3::NrMacSchedulerTdmaRR"))`; the options are `NrMacScheduler{Tdma,Ofdma}{RR,PF,MR}` plus QoS-aware and AI-based variants in the model directory. It must be set before `InstallGnbDevice`. Scheduler attributes are set with `SetSchedulerAttribute("FixedMcsDl", BooleanValue(true))` and similar.
- TDMA schedulers give each symbol to a single UE; OFDMA schedulers can share a symbol among UEs in frequency. The choice changes latency and fairness, especially with analog beamforming.
- Bearers are QoS flows since v4.2: `NrQosFlow flow(NrQosFlow::NGBR_LOW_LAT_EMBB)`, a `Ptr<NrQosRule>` with `NrQosRule::PacketFilter` (`localPortStart`, `localPortEnd`), and `nr->ActivateDedicatedQosFlow(ueDev, flow, rule)`. `ActivateDataRadioBearer(ueDev, flow)` activates a bearer without a filter.
- Typical traffic: `UdpClientHelper` on the remote host to `UdpServerHelper` on UEs (downlink), or the traffic generators in `traffic-generator-example`, XR traffic in `cttc-nr-traffic-3gpp-xr`. Set RLC buffer sizes (`ns3::NrRlcUm::MaxTxBufferSize`) so the radio, not the buffer, limits packet loss.
- Core network delay: `epc->SetAttribute("S1uLinkDelay", TimeValue(MilliSeconds(0)))` removes the backhaul delay in the demo. State the value used when reporting end-to-end latency.
- Measure end-to-end metrics with `FlowMonitor` installed on the remote host and the UEs, as the demo does, plus the nr traces below for radio-level detail.

## 7. Handover

Verified in the v5.1 branch (helper, models, tests) and in `RELEASE_NOTES.md`:

- NR-to-NR handover over the X2 interface is implemented in nr. The model classes are `NrGnbRrc`, `NrEpcX2`, `NrHandoverAlgorithm` and the algorithms `NrA3RsrpHandoverAlgorithm`, `NrA2A4RsrpHandoverAlgorithm` and `NrNoOpHandoverAlgorithm`.
- The default `NrHelper::HandoverAlgorithm` is `ns3::NrNoOpHandoverAlgorithm`, so no automatic handover happens unless an algorithm is selected. Handover needs the EPC (`SetEpcHelper`).
- v5.0 notes: "major overhaul of the handover, RRC and radio-link-failure machinery", inter-frequency and inter-numerology handover, cell individual offset (CIO) biasing including negative offsets. v5.1 notes: handover between FDD cells, handover command carrying the target UL carrier and RACH configuration, handover metrics, a TR 36.839 failure model (disabled by default), optional admission floors (`MinTargetRsrpDbm`, `MinTargetRsrqDb`) and a ping-pong guard (`HandoverMinTimeOfStay`), mobility state estimation scaling the A3 time-to-trigger (disabled by default).
- NR-to-LTE (inter-RAT) handover is not mentioned in the release notes; do not assume it. For LTE-only handover use the upstream `lte` module (`LteHelper`, `A3RsrpHandoverAlgorithm`, examples `lena-x2-handover`).
- Releases before v5.0 have a smaller handover feature set; read the `CHANGES.md` of the release in use before relying on a feature.
- The nr examples directory of v5.1 has no dedicated handover example; the templates are the tests, for example `test/nr-test-x2-handover.cc` (scripted handover), `nr-test-inter-freq-handover.cc` and `nr-test-handover-scenarios.cc`.

```cpp
// Algorithm type and attributes are read when gNB devices are installed
nr->SetHandoverAlgorithmType("ns3::NrA3RsrpHandoverAlgorithm");
nr->SetHandoverAlgorithmAttribute("Hysteresis", DoubleValue(3.0));              // dB, default 3.0
nr->SetHandoverAlgorithmAttribute("TimeToTrigger", TimeValue(MilliSeconds(256)));  // default 256 ms
// ... InstallGnbDevice, InstallUeDevice, AssignUeIpv4Address, AttachToClosestGnb ...
nr->AddX2Interface(gnbNodes);          // after the gNB devices exist; links every gNB pair

// Scripted handover instead of an algorithm (NoOp algorithm selected):
nr->HandoverRequest(Seconds(1.5), ueDevs.Get(0), gnbDevs.Get(0), gnbDevs.Get(1));
```

- UEs must move (for example `ConstantVelocityMobilityModel`) for A3 events to occur; static UEs never hand over with an A3 algorithm.
- Radio link failure uses `ns3::NrUeRrc::N310`, `N311` and `T310`; the handover test raises them to disable RLF during scripted handovers when the real (non-ideal) RRC is used. Gate any use of these attributes on `./ns3 show typeid ns3::NrUeRrc`.
- The helper API keeps the name "X2" although the NR interface between gNBs is called Xn in 3GPP; interface semantics are in 5g-nr-3gpp-expert.
- Evaluate handover with the traces that report RLF causes and total handover time (added in v5.1) and by the packets lost or delayed around the event, from PDCP traces or per-flow throughput over time.
- After upgrading nr, run the nr test suites that cover your scenario (`./test.py --list` shows suite names, `./test.py -s <suite>` runs one), since handover logic changed in v5.0 and v5.1.

## 8. Traces and statistics

- `nr->EnableTraces()` switches on the standard set: DL data and control PHY traces, UL PHY traces, RLC and PDCP simple and end-to-end traces, PHY and MAC control message traces, DL and UL MAC scheduling traces and pathloss traces. Individual calls exist for each (`EnableDlDataPhyTraces()`, `EnableRlcE2eTraces()`, `EnablePdcpE2eTraces()` and others). Call after devices are installed.
- Output goes to files in the working directory (some through SQLite, which needs SQLite support at configure time). Use `./ns3 run --cwd=<dir>` to keep files per run, and a `simTag` argument as the demo does so campaigns do not overwrite each other.
- Hook trace sources directly for custom metrics, for example `RxPacketTraceUe` on `NrUePhy/SpectrumPhy` as `EnableDlDataPhyTraces` does; names are in `./ns3 show typeid ns3::NrSpectrumPhy`.
- Per-slot traces are large. With many UEs and all traces enabled the output files become very large; enable only the layers needed.
- Pathloss and SINR traces separate the channel from the scheduler and let a result be explained.

## 9. API drift and common errors

| Symptom | Cause and fix |
|---|---|
| Compile error: `InitializeOperationBand`, `ActivateDedicatedEpsBearer`, `NrEpsBearer`, `NrEpsBearerTft` not found | These names belong to older releases. v5.1 uses `CreateOperationBandContiguousCc` plus `NrChannelHelper::AssignChannelsToBands`, `ActivateDedicatedQosFlow`, `NrQosFlow`, `NrQosRule` |
| `NumRbPerRbg` / `RbOverhead` not found on `NrGnbMac` / `NrGnbPhy` | Moved to `NrHelper` in v5.0 |
| `NrRlcUm::OutOfOfOrderDelivery` not found | Renamed `OutOfOrderDelivery` in v5.0 |
| `EnableMimoFeedback` not found | Removed in v4.1.1; copy the MIMO setup from `cttc-nr-mimo-demo` of the release in use |
| Compile errors in ns-3 core after updating only one repository | nr and ns-3 releases do not match; see section 1 |
| UEs never attach, zero throughput | Applications start before attachment; positions out of coverage (check TX power and the channel scenario); EPC or IP stack not installed on UEs |
| Throughput far below the carrier capacity | RLC buffer too small, TDD pattern or scheduler, a single UE with analog beamforming, or application rate below capacity; check with RLC and MAC traces |
| Very slow simulation | Many UEs with 3GPP fading and 64x32-element arrays; reduce arrays, update periods, UEs, or use the faster 3GPP channel MR noted in the release notes |
| Results change after upgrading nr | Models were fixed between releases (beam scan, SRS filtering, FDD power); rerun baselines and document the version |
| Reproducibility lost after adding a node | Automatic stream assignment; use `AssignStreams` with fixed bases |

- Search the examples and tests of the release in use before writing new configuration; most attribute names in published papers refer to older releases.
- Keep scenario parameters (frequency, bandwidth, numerology, TX power, antenna sizes, scheduler) in one printed block at program start so a result file carries its configuration.
