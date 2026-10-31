---
name: ns3-expert
description: >-
  Builds, runs and debugs ns-3 network simulations (3.49) in C++: the ./ns3 CMake wrapper, scratch and contrib programs, attributes and Config paths, CommandLine, trace sources, PCAP, FlowMonitor, NS_LOG, seeds and run numbers for independent replications, and the 5G-LENA nr module (v5.1, ns-3.48) with its handover support. Use when editing ns-3 scratch or contrib code, running ./ns3 configure, build or run, or setting RngSeed and RngRun. Not for 3GPP spec interpretation (use 5g-nr-3gpp-expert), statistics of results (use statistics-expert), general C++ (use cpp-expert), or plotting (use scientific-python-expert).
license: MIT
metadata:
  version: "3.2.0"
---

# ns-3 Expert

This skill covers discrete-event network simulation with ns-3: building and running with the `ns3` script, writing C++ scenarios with helpers, attributes and trace sinks, collecting results with FlowMonitor, PCAP and custom traces, controlling randomness for reproducible independent replications, and the CTTC 5G-LENA `nr` contrib module including what it does and does not support for handover. The LTE module and Python bindings are covered briefly. Interpretation of 3GPP specifications, statistical analysis of output and plotting belong to other skills.

> Verified against ns-3.49 (tag ns-3.49, release notes and source read; g++ 11.1+ or clang 17+, CMake 3.25+, Python 3.10+, C++23 default) and the nr module v5.1 (branch 5g-lena-v5.1.y, requires ns-3.48; v5.0 ns-3.48, v4.2 ns-3.47, v4.1.1 ns-3.46) (2026-10).

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

- Covered: the `ns3` wrapper (`configure`, `build`, `run`, `show`, `clean`), build profiles and module selection, C++ scenario scripts in `scratch/` and `contrib/`, helpers, attributes, `Config::SetDefault`/`Set`/`Connect`, `CommandLine`, trace sources and sinks, PCAP and ASCII traces, FlowMonitor, `NS_LOG`, random variables, `RngSeedManager`, `RngSeed`/`RngRun`, stream assignment, sweep scripts, and the `nr` module (NrHelper, operation bands, bandwidth parts, beamforming, QoS flows, X2 handover).
- Brief: the upstream `lte` module (for comparison with nr) and the cppyy-based Python bindings.
- Not covered: meaning of 3GPP procedures, numerology tables, link budgets and spec clauses (5g-nr-3gpp-expert); confidence intervals, number of replications, warm-up deletion and hypothesis tests (statistics-expert); general C++ language, templates and tooling (cpp-expert); figures and data wrangling of results (scientific-python-expert); container images and CI (docker-expert, cicd-expert).

## 2. Core Expertise

| Area | Key facts |
|---|---|
| Releases | ns-3.49 is the newest release (GitLab tag, 2026-10); earlier: 3.48 (2026-06), 3.47 (2026-02), 3.46.1 and 3.46 (2025-10). Release notes in `RELEASE_NOTES.md`, API changes in `CHANGES.md` of each tag. Default C++ standard is C++23 (since 3.46); `wimax` was removed in 3.46 |
| ns3 script | Subcommands `configure`, `build`, `run`, `clean`, `distclean`, `show`, `shell`, `docs`, `install`. Run options: `--no-build`, `--cwd`, `--gdb`, `--lldb`, `--valgrind`, `--command-template`, `--enable-sudo`. Program arguments follow `--` or are quoted with the target |
| Build profiles | `debug`, `default` (asserts and logs on), `release`, `optimized` (release plus `-march=native`), `minsizerel`. Logs and asserts are compile-time options (`--enable-logs`, `--enable-asserts`) |
| Attributes | Every configurable parameter is an Attribute of a TypeId. Level 1 `Config::SetDefault`, level 2 helper `SetXAttribute`, level 3 `Config::Set`/`SetAttribute` on objects. Discover with `--PrintAttributes=ns3::X` or `./ns3 show typeid ns3::X` |
| Tracing | Trace sources are named hooks; sinks are callbacks connected with `Config::ConnectWithoutContext`, `Config::Connect` or `TraceConnect*`. Helpers write PCAP (`EnablePcapAll`) and ASCII (`EnableAsciiAll`) |
| FlowMonitor | `FlowMonitorHelper::Install`/`InstallAll`, `CheckForLostPackets()`, `GetFlowStats()`, `Ipv4FlowClassifier::FindFlow`, `SerializeToXmlFile` |
| Logging | `NS_LOG="Component=level_info\|prefix_time"` (builds with logs only). In 3.49 `function` became the most verbose level; `level_logic` no longer includes function traces |
| Randomness | MRG32k3a streams. Defaults `RngSeed=1`, `RngRun=1`; vary `RngRun` with a fixed seed for independent replications. `Stream` attribute pins a variable; `AssignStreams` on helpers assigns ranges |
| nr module | CTTC 5G-LENA in `contrib/nr`; v5.1 (2026-08) needs ns-3.48. NrHelper, NrPointToPointEpcHelper, CcBwpCreator, NrChannelHelper, IdealBeamformingHelper, NrQosFlow |
| nr handover | NR-to-NR handover over X2 is implemented (A3 RSRP, A2-A4 RSRP, no-op algorithms; scripted `HandoverRequest`); inter-frequency and inter-numerology since v5.0, FDD cells since v5.1. NR-to-LTE handover is not documented; no dedicated handover example in v5.1 examples (tests serve as templates) |
| LTE module | `LteHelper`, `PointToPointEpcHelper`, `A3RsrpHandoverAlgorithm`, X2 handover examples (`lena-x2-handover`) in upstream ns-3 |
| Python | cppyy-based bindings (cppyy 3.5.0 or later, Python 3.10+, Linux only tested); C++ remains the main route |

## 3. Workflow

1. Identify the versions first: `./ns3 show version`, `git describe --tags --always`, and for nr the branch in `contrib/nr`. Match nr to its ns-3 release (section 2 and the nr reference). State the versions in the answer.
2. Read the existing scenario, `CMakeLists.txt` in `scratch/` or the module, and the `ns3rc` or configure options used. Check the build profile with `./ns3 show profile` before judging speed or missing logs.
3. Find the real API in the checked-out source: look in `examples/`, `src/<module>/model|helper/*.h`, and `./ns3 show typeid`. Do not write helper or attribute names from memory, since nr and some ns-3 helpers changed between releases.
4. Make the smallest change that reproduces the behaviour. Set defaults and attributes before creating objects; connect traces after objects exist.
5. Build with `./ns3 build <target>` and run with `./ns3 run --no-build ... -- args` in a per-run directory. Check the exit code and the first lines of output.
6. For measurement work: set the run number explicitly, run a short pilot, confirm determinism (same run twice gives identical output), then launch the sweep (reference: reproducible-experiments).
7. Report the commands run, the versions, the seed and run numbers, and anything not verified.

## 4. Decision Rules

- If the project pins an ns-3 release, stay on it; for a new study use the newest release that the needed contrib modules support (nr v5.1 needs ns-3.48 even though 3.49 exists).
- If results will be published or compared, use a release tag or recorded commit, never an unpinned master.
- If you need many runs, build once (`release` or `optimized` profile) and run with `--no-build`; if you need to debug, use `debug` or `default` and `--enable-sanitizers`.
- If a parameter must be varied from a script, expose it through `CommandLine` or an attribute path; do not edit source per run.
- If you need independent replications, keep `RngSeed` fixed and change `RngRun`; do not choose seeds from the clock.
- If two variants must see the same randomness (paired comparison), pin streams with `AssignStreams` and the `Stream` attribute, otherwise adding a node shifts every later automatic stream.
- If a metric is per flow at the IP layer, use FlowMonitor on end nodes; if it needs packet-level or radio-level detail, connect trace sources or enable the module's traces.
- If a trace sink is needed on an object that does not exist yet (a TCP socket), connect it from a scheduled event after creation.
- If the task is a 5G system-level study, use nr; if it is an LTE baseline or a comparison, the upstream `lte` module or nr's `lena-lte-comparison` example can be used; nr does not depend on upstream `lte`.
- If handover is required in nr, use NR-to-NR with the X2 interface and an A3 or A2-A4 algorithm; verify any other handover claim in the release's `CHANGES.md` and tests before promising it.
- If the question is about a 3GPP procedure rather than how the simulator models it, hand it to 5g-nr-3gpp-expert; if it is about confidence intervals or the number of runs, hand it to statistics-expert.

## 5. Coding Standards

- Follow the ns-3 C++ style used in the tree (clang-format with the repository `.clang-format`; 4-space indent, braces on their own line, `Ptr<T>` for objects, `CreateObject<T>()`, `NS_LOG_COMPONENT_DEFINE`). Releases enforce clang-format 20 to 22 in their own tree; study code can use the same file.
- Include module headers (`"ns3/core-module.h"`, `"ns3/nr-module.h"`) in scenario files and `using namespace ns3;`; in library code include only the headers needed.
- Declare every tunable as a `CommandLine` argument with a description and a typed default; use `Time` for durations (`--simTime=10s`), not bare doubles in seconds.
- Create objects in this order: defaults and `CommandLine`, nodes, mobility, devices, internet stack and addresses, applications, traces, `Simulator::Stop`, `Run`, results, `Destroy`.
- Use `ns3::Ptr` and ns-3 containers; do not store raw pointers to objects across events; use `Simulator::Schedule` with `MakeEvent` or member-function overloads for deferred work.
- Use ns-3 random variables (`CreateObject<UniformRandomVariable>()`) for all randomness; never `rand()`, `std::random_device` or time-based seeds.
- Use `NS_LOG_*` for diagnostics and `NS_ASSERT_MSG` / `NS_ABORT_MSG_IF` for invariants; no side effects inside log or assert expressions.
- Match trace sink signatures to the documented callback type; name sinks `OnX` or `XSink`.
- Write results to files in the working directory (CSV with a header, one row per run or flow), not to stdout.
- Keep model code (classes with attributes and trace sources registered via `TypeId`) separate from scenario code (`main`).

## 6. Project Structure

```text
ns-3-dev/                       # pinned release checkout (git tag)
  contrib/nr/                   # nr module on the matching release branch
  scratch/
    my-study/                   # one program: directory with main()
      my-study.cc
      scenario.h  scenario.cc
  build/  cmake-cache/          # generated, not committed
study-repo/                     # separate Git repository for the study
  scenario/                     # sources copied or linked into scratch/
  scripts/sweep.sh              # build once, run many with --RngRun
  config/                       # parameter files, one per campaign
  results/<campaign>/<params>_run<k>/   # stdout.log, result.csv, STATUS
  manifest.txt                  # versions, commits, command line
```

- Keep study code outside the ns-3 tree under version control, and record the ns-3 and nr commits in the manifest.
- A new module belongs in `contrib/<name>/` with `model/`, `helper/`, `examples/`, `test/` and a `CMakeLists.txt` using `build_lib`; `utils/create-module.py` creates the skeleton.
- Do not commit `build/` or `cmake-cache/`. Never patch files under `src/` for a study without storing the patch.

## 7. Design Patterns

- **Helper plus attributes**: configure through helpers (`PointToPointHelper`, `NrHelper`), install on containers, keep topology construction in a function that returns containers.
- **Scenario struct**: collect all parameters in one struct filled from `CommandLine`; print it at start and write it into the results file.
- **Trace sink with bound state**: `MakeBoundCallback(&Sink, stream)` or a small class holding counters, so sinks do not use globals.
- **Per-run directory**: every run writes into its own directory (`--cwd`), keeping PCAP, XML and CSV together with the exact command.
- **Experiment driver script**: a shell or Python script owns loops over parameters and run numbers; the C++ program does one run. See [references/reproducible-experiments.md](references/reproducible-experiments.md).
- **Stream ranges**: allocate distinct stream index blocks per random source (mobility, traffic, channel, scheduler) via `AssignStreams`, leaving gaps.
- **Measurement window**: record statistics only after a warm-up period (start FlowMonitor with `StartTime` or ignore early samples) and stop applications before `Simulator::Stop` so queues drain.
- **Config store for documentation**: dump all attribute values at the start of a campaign with the config store.

## 8. Best Practices

- Pin versions, record them, and rerun a baseline after any ns-3 or nr upgrade; models are fixed between releases and numbers shift.
- Use `./ns3 run ... -- --PrintHelp` and `--PrintAttributes` to confirm names; Doxygen lists trace sources with their callback signatures.
- Set `Simulator::Stop` explicitly; applications that never stop keep the event queue busy.
- Start traffic after network attachment or routing setup; the first packets of a cellular scenario fail otherwise.
- Install FlowMonitor on end nodes only to avoid counting a packet at every hop.
- Enable only the PCAP and traces you analyse; per-packet tracing on all devices dominates run time.
- Run a short pilot with detailed logs, then the campaign with logs off.
- Validate with simple cases: one link, known rate, expected throughput and delay; conservation of packets (sent equals received plus dropped).
- Check that loss, delay and throughput agree between two independent sources (an application sink and FlowMonitor).
- Treat a model default as a modelling choice: print and justify values such as TX power, buffer sizes, MTU, queue discipline.

## 9. Performance

- Use the `release` or `optimized` profile for campaigns; `default` and `debug` are slower. Logging and assertions cost time even when disabled at run time in builds that compile them in.
- Build only the modules you need (`--enable-modules`) and keep examples and tests off unless required; link time is a large part of rebuilds (`NS3_FAST_LINKERS` uses mold or lld when installed, `NS3_CCACHE` uses ccache).
- Run replications as independent processes, one per core; a single ns-3 simulation is single-threaded unless MPI is enabled. Memory per process limits `-j` more than CPU count for nr and wifi.
- Cost scales with the number of nodes times events: reduce simulated time, UEs, antenna elements (nr arrays of 4x8 or more) and fading update rates only when the study allows it, and say so.
- 3GPP channel computation dominates large nr runs; ns-3.49 notes a roughly 8 to 11 times per-link speedup for the 3GPP spectrum model with unchanged results. The nr v5.0 notes recommend ns-3 MR !2883 for older trees.
- Avoid per-packet `std::cout`, `std::endl` and large in-memory vectors in sinks; aggregate counters and write at the end.
- Profile with `./ns3 run ... --perf` or `--heaptrack` before tuning; do not guess.

## 10. Security

- Treat command-line values and input files (mobility traces, config store files) as untrusted when a service launches simulations: validate numeric ranges, build output paths from a fixed base directory, and never pass user text to `system()` or a shell.
- Quote every variable in sweep scripts (`"$dir"`), use `set -euo pipefail`, build argument lists as arrays, and never `eval` parameter strings.
- Do not run simulations as root. `./ns3 configure --enable-sudo` / `run --enable-sudo` sets suid bits on executables for emulation devices (TAP, EMU, raw sockets); use it only inside a disposable VM or container and revert with a clean reconfigure.
- Emulation modes (`TapBridge`, `FdNetDevice`) touch the host network; run them in an isolated network namespace, not on a production host.
- Fetch dependencies from the official repositories (gitlab.com/nsnam, gitlab.com/cttc-lena) by tag or commit, and review third-party contrib modules and App Store modules before building; they execute at build time and run time with your privileges.
- Do not put credentials in scenario files or results; results often get shared.
- Keep sanitizer builds (`--enable-sanitizers`) in CI for custom models to catch memory errors that become security bugs in emulation use.

## 11. Testing

- ns-3 test runner: `./ns3 configure --enable-tests --enable-examples`, then `./test.py` (all), `./test.py -s <suite>` (one suite), `./test.py --list`, `./test.py --help`. Test suites are `TestSuite`/`TestCase` classes with `NS_TEST_ASSERT_MSG_EQ`, `NS_TEST_ASSERT_MSG_EQ_TOL` and similar macros.
- For custom models add a suite under `contrib/<module>/test/`. Fix the seed and run in the test, assert counters and tolerances, not exact floating-point output of a whole scenario.
- Regression-test a scenario by running it twice with the same `--RngRun` and comparing result files byte for byte, and with two different run numbers expecting a difference.
- Add analytic sanity tests: a saturated point-to-point link delivers close to the link rate minus header overhead; a single UE in free space has the expected path loss.
- Run nr's own tests after changing nr or ns-3 versions; handover behaviour is covered by `nr-test-x2-handover` and related suites in `contrib/nr/test`.
- Test the sweep script with 2 runs and a 1 s simulation before launching the full campaign.
- Run the examples as well after a toolchain upgrade to detect behaviour changes; `./test.py --help` lists the options for examples.

## 12. Review Checklist

- [ ] ns-3 release or commit, nr branch, compiler and profile are recorded and compatible.
- [ ] `CommandLine` exposes every tunable; defaults are printed or stored with results.
- [ ] No `RngRun` or `RngSeed` hard-coded after `cmd.Parse`; independent runs differ, repeated runs match.
- [ ] No `rand()`, `std::random_device`, clock-based seeds or iteration over pointer-keyed unordered containers.
- [ ] Defaults and attributes are set before the objects they affect are created.
- [ ] Trace sink signatures match the source; sinks are cheap; connections happen after the objects exist.
- [ ] Applications start after routing or attachment is ready and stop before `Simulator::Stop`.
- [ ] FlowMonitor installed on the intended nodes; `CheckForLostPackets()` called; lost-packet definition stated.
- [ ] Warm-up and measurement window are defined; the metric definitions (delay, jitter, throughput) are written down.
- [ ] Outputs go to a per-run directory; the exit status of each run is checked.
- [ ] For nr: bandwidth parts, numerology, TX power split, antenna sizes, scheduler and channel scenario are printed; handover claims match the release.
- [ ] No secrets, `sudo` suid builds or host-network emulation outside an isolated environment.

## 13. Production Notes

- Reproduce a result with: ns-3 tag or commit, nr commit, local patch, build profile, compiler version, full command line with `RngSeed` and `RngRun`, and input files with checksums. Keep these in `manifest.txt` beside the results.
- Prefer a container or a locked toolchain for campaigns; floating-point output can differ with compiler and flags (`optimized` uses `-march=native`).
- On clusters, use one process per run, a shared read-only build tree, a per-run output directory, and job arrays mapped to `--RngRun`. Check free disk space; PCAP and nr traces grow fast.
- Make the driver restartable: skip runs whose `STATUS` file says `ok`; list failed runs at the end.
- Upgrade plan for ns-3.49: logging level ordering changed (use `level_logic|function` for the former `level_logic`); `CommandLine` keeps spaces in `std::string` values; `Config::SetDefault` accepts parent TypeId attributes via derived names; `TypeTraits` and some `Ipv4InterfaceAddress` secondary-address functions were removed; pcap helpers use `iana::LinkType`.
- Upgrade plan for nr 5.0 and 5.1: `NumRbPerRbg` and `RbOverhead` moved to `NrHelper`; `OutOfOfOrderDelivery` renamed `OutOfOrderDelivery`; `AssignStreams` takes a parameter struct; FDD setup is mostly automatic in 5.1. Older tutorials with `InitializeOperationBand` or EPS bearer calls do not compile on v5.1.
- ns-3 website pages (nsnam.org) were not reachable when this skill was written, so release dates come from GitLab tags and the examples were read against the sources but not compiled; confirm the current stable release on the project site and build the examples before relying on them.

## 14. Examples

A two-node scenario that takes its run number from `--RngRun`, measures with FlowMonitor and writes one CSV row (C++ for ns-3.49; not compiled here):

```cpp
#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"

#include <fstream>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("TwoNodeFlow");

int
main(int argc, char* argv[])
{
    Time simTime = Seconds(20);
    std::string rate = "5Mbps";
    std::string linkRate = "10Mbps";

    CommandLine cmd(__FILE__);
    cmd.AddValue("simTime", "Simulated time", simTime);
    cmd.AddValue("rate", "Mean offered rate of the source", rate);
    cmd.AddValue("linkRate", "Bottleneck link rate", linkRate);
    cmd.Parse(argc, argv); // --RngSeed and --RngRun are read here as global values

    NodeContainer nodes;
    nodes.Create(2);
    PointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue(linkRate));
    p2p.SetChannelAttribute("Delay", StringValue("2ms"));
    NetDeviceContainer devs = p2p.Install(nodes);

    InternetStackHelper stack;
    stack.Install(nodes);
    Ipv4AddressHelper addr;
    addr.SetBase("10.1.1.0", "255.255.255.0");
    Ipv4InterfaceContainer ifs = addr.Assign(devs);

    const uint16_t port = 9000;
    OnOffHelper onoff("ns3::UdpSocketFactory", InetSocketAddress(ifs.GetAddress(1), port));
    onoff.SetAttribute("DataRate", StringValue(rate));
    onoff.SetAttribute("PacketSize", UintegerValue(1200));
    onoff.SetAttribute("OnTime", StringValue("ns3::ExponentialRandomVariable[Mean=0.5]"));
    onoff.SetAttribute("OffTime", StringValue("ns3::ExponentialRandomVariable[Mean=0.5]"));
    ApplicationContainer src = onoff.Install(nodes.Get(0));
    src.Start(Seconds(1));
    src.Stop(simTime);

    PacketSinkHelper sinkHelper("ns3::UdpSocketFactory",
                                InetSocketAddress(Ipv4Address::GetAny(), port));
    ApplicationContainer sink = sinkHelper.Install(nodes.Get(1));
    sink.Start(Seconds(0));

    FlowMonitorHelper fm;
    Ptr<FlowMonitor> monitor = fm.InstallAll();

    Simulator::Stop(simTime + Seconds(1));
    Simulator::Run();

    monitor->CheckForLostPackets();
    uint64_t tx = 0;
    uint64_t rx = 0;
    for (const auto& [id, st] : monitor->GetFlowStats())
    {
        tx += st.txPackets;
        rx += st.rxPackets;
    }
    Ptr<PacketSink> ps = DynamicCast<PacketSink>(sink.Get(0));
    double mbps = ps->GetTotalRx() * 8.0 / (simTime - Seconds(1)).GetSeconds() / 1e6;

    std::ofstream out("result.csv");
    out << "seed,run,rate,linkRate,txPackets,rxPackets,goodputMbps\n"
        << RngSeedManager::GetSeed() << "," << RngSeedManager::GetRun() << "," << rate << ","
        << linkRate << "," << tx << "," << rx << "," << mbps << "\n";
    monitor->SerializeToXmlFile("flowmon.xml", true, true);

    Simulator::Destroy();
    return 0;
}
```

Build once and run three independent replications in separate directories:

```bash
./ns3 build scratch/two-node-flow
for run in 1 2 3; do
  mkdir -p "results/run${run}"
  ./ns3 run --no-build scratch/two-node-flow --cwd "results/run${run}" -- \
    --RngRun="${run}" --rate=5Mbps > "results/run${run}/stdout.log"
done
```

Selecting the scheduler and handover algorithm in nr v5.1 (set before the gNB devices are installed; see the reference for the full scenario):

```cpp
nr->SetSchedulerTypeId(TypeId::LookupByName("ns3::NrMacSchedulerTdmaRR"));
nr->SetHandoverAlgorithmType("ns3::NrA3RsrpHandoverAlgorithm");
nr->SetHandoverAlgorithmAttribute("TimeToTrigger", TimeValue(MilliSeconds(256)));
// ... InstallGnbDevice / InstallUeDevice / AttachToClosestGnb ...
nr->AddX2Interface(gnbNodes);
```

Logging for one run (needs a build with logs enabled):

```bash
NS_LOG="TwoNodeFlow=level_info|prefix_time:PacketSink=level_info" ./ns3 run scratch/two-node-flow
```

## 15. Common Mistakes

- **Calling `RngSeedManager::SetRun(1)` in `main` and then passing `--RngRun`**: the code overrides the argument, so all replications are identical. Do not set the run in code.
- **Choosing seeds from the clock or varying the seed instead of the run**: results cannot be repeated, and streams from different seeds may overlap. Fix the seed and vary `RngRun`.
- **Using `rand()` or `std::random_device` in model code**: breaks reproducibility. Use ns-3 random variables.
- **Setting `Config::SetDefault` after the objects are created**: no effect on existing objects. Set defaults first.
- **Trace sink signature not matching**: compile error or fatal error at connect time. Copy the callback signature from Doxygen.
- **`Config::Connect` before the node or device exists**: the path matches nothing. Build the topology first, or connect from a scheduled event.
- **NS_LOG output missing**: the build has logs off (`release`/`optimized`) or the component name is wrong. Check `./ns3 show profile`.
- **Using `level_function` or `level_logic` strings from older notes on 3.49**: the level ordering changed; use `level_logic|function` to get the former `level_logic` output.
- **Applications without a stop time and `Simulator::Stop` too early**: truncated flows and lost-packet counts. Stop sources before the simulation ends and use `CheckForLostPackets()`.
- **FlowMonitor installed everywhere on a cellular scenario**: tunnelled traffic is counted at several hops. Install it on the remote host and UEs.
- **Mixing nr and ns-3 releases (for example nr v5.1 with ns-3.49)**: compile errors or silent behaviour changes. Use the pair in the compatibility table.
- **Using old nr API from tutorials (`InitializeOperationBand`, `ActivateDedicatedEpsBearer`)**: replaced in v4.2 to v5.1; copy from the examples of the release in use.
- **Assuming NR-to-LTE handover or FDD handover exists in every release**: NR-to-NR handover is documented from the release notes; FDD handover is new in v5.1 and inter-RAT is not documented. Verify in `CHANGES.md` and tests.
- **Comparing numbers from the `default` and `optimized` profiles across machines**: compiler flags change floating-point results; compare like with like.
- **Writing PCAP to a directory that does not exist or sharing one output name between parallel runs**: files fail to open or get overwritten. Use per-run directories.
- **Forgetting `Simulator::Destroy()`**: objects are not cleaned up and memory-check tools report leaks; trace files may not flush.

## 16. References

- [references/build-and-run.md](references/build-and-run.md): requirements, the ns3 script commands and options, build profiles, module selection, scratch and contrib layout, debugging, Python bindings, build error table.
- [references/tracing-and-output.md](references/tracing-and-output.md): CommandLine, attributes and Config paths, trace sources and sinks, PCAP and ASCII, FlowMonitor, NS_LOG syntax and the 3.49 level change, output hygiene.
- [references/nr-5g-lena.md](references/nr-5g-lena.md): nr versions and ns-3 compatibility, installation in contrib, v5.1 scenario skeleton, bandwidth parts, beamforming, schedulers and QoS flows, handover support, traces, API drift.
- [references/reproducible-experiments.md](references/reproducible-experiments.md): seeds, runs and streams, independent replications, common random numbers, sources of non-determinism, a sweep script, what to record, validation checks.
- ns-3 project: https://www.nsnam.org/ ; source and releases: https://gitlab.com/nsnam/ns-3-dev ; documentation (manual, tutorial, model library, Doxygen) on the project site.
- nr module (5G-LENA): https://gitlab.com/cttc-lena/nr (README, `CHANGES.md`, `RELEASE_NOTES.md`) and https://5g-lena.cttc.es/
- 3GPP questions: use 5g-nr-3gpp-expert; statistical treatment of replications: use statistics-expert; plotting: use scientific-python-expert.
