# Attributes, Tracing and Output in ns-3

How to configure objects (attributes, `Config` paths, `CommandLine`), observe them (trace sources, sinks, PCAP, ASCII, FlowMonitor) and control log output with `NS_LOG`. API names checked against the ns-3.49 sources in 2026-10.

## Contents

1. [CommandLine](#1-commandline)
2. [Attributes and Config paths](#2-attributes-and-config-paths)
3. [Trace sources and sinks](#3-trace-sources-and-sinks)
4. [PCAP and ASCII traces](#4-pcap-and-ascii-traces)
5. [FlowMonitor](#5-flowmonitor)
6. [Logging](#6-logging)
7. [Output hygiene](#7-output-hygiene)

## 1. CommandLine

```cpp
uint32_t nUe = 4;
Time simTime = Seconds(10);
bool tracing = false;
std::string outDir = ".";

CommandLine cmd(__FILE__);
cmd.AddValue("nUe", "Number of UEs", nUe);
cmd.AddValue("simTime", "Simulation duration", simTime);
cmd.AddValue("tracing", "Write PCAP files", tracing);
cmd.AddValue("outDir", "Output directory", outDir);
cmd.AddValue("anti", "ns3::RandomVariableStream::Antithetic");  // name + attribute path
cmd.Parse(argc, argv);
```

- Call `cmd.Parse` before creating objects whose configuration depends on the values, and before any code that reads `RngSeedManager`.
- Accepted forms: `--name=value` and `--name value`. `Time` values need a unit (`--simTime=10s`, `--simTime=500ms`). Booleans accept `--tracing` or `--tracing=1`.
- Built-in switches: `--PrintHelp`, `--PrintVersion`, `--PrintGlobals`, `--PrintGroups`, `--PrintGroup=<group>`, `--PrintTypeIds`, `--PrintAttributes=<ns3::TypeId>`. `--PrintHelp` also lists the program's own arguments with their defaults.
- Global values are settable from the command line without `AddValue`: `--RngSeed=N`, `--RngRun=N`, `--SimulatorImplementationType=ns3::...`, `--ChecksumEnabled`.
- `cmd.AddValue("name", "ns3::Class::Attribute")` (two strings) binds an argument to an attribute default; the value is applied with `Config::SetDefaultFailSafe`, so it affects objects created afterwards.
- Since ns-3.49, `std::string` arguments with spaces are no longer cut at the first space.
- `CommandLine` rejects arguments it does not know and prints the usage text, so a typo in a sweep script stops the run. Pass program arguments after `--` when using `./ns3 run`.

## 2. Attributes and Config paths

Everything configurable is an Attribute on a TypeId. Three levels:

```cpp
// 1. Defaults for objects created later (before any helper creates them)
Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(1448));
Config::SetDefault("ns3::OnOffApplication::PacketSize", UintegerValue(1200));

// 2. Helper-level, applied when the helper creates objects
PointToPointHelper p2p;
p2p.SetDeviceAttribute("DataRate", StringValue("10Mbps"));
p2p.SetChannelAttribute("Delay", StringValue("2ms"));

// 3. Object level, after creation
dev->SetAttribute("DataRate", DataRateValue(DataRate("20Mbps")));
Config::Set("/NodeList/*/DeviceList/*/$ns3::PointToPointNetDevice/DataRate",
            StringValue("20Mbps"));
```

- Look up names and types instead of guessing: `./ns3 run "scratch/x --PrintAttributes=ns3::PointToPointNetDevice"` or `./ns3 show typeid ns3::PointToPointNetDevice`, or the Doxygen "Attributes" tables.
- Values: `UintegerValue`, `IntegerValue`, `DoubleValue`, `BooleanValue`, `StringValue` (parsed by the attribute checker, so `"10Mbps"` and `"2ms"` work), `TimeValue`, `DataRateValue`, `PointerValue`, `TypeIdValue`, `AddressValue`, `EnumValue`. A string form such as `"ns3::UniformRandomVariable[Min=0|Max=1]"` creates a random variable through `StringValue`.
- `Config::SetDefault` fails with a fatal error on a wrong name (use `SetDefaultFailSafe` to test); since 3.49 it also accepts an attribute declared by a parent TypeId when called with the derived type name.
- Config path syntax: `/NodeList/<index or *>/DeviceList/<index or *>/<attribute or trace source>`; `$ns3::Type` selects an aggregated object by type (`/NodeList/0/$ns3::MobilityModel/...`); `/Names/<name>` after `Names::Add("name", obj)`. A path that matches nothing is an error in `Config::Set`, so a typo is caught at run time.
- Set defaults before creating helpers and nodes; changing a default afterwards does not affect objects that already exist.
- `GlobalValue` objects (`RngSeed`, `RngRun`, `SimulatorImplementationType`, `ChecksumEnabled`) are set with `Config::SetGlobal` or `NS_GLOBAL_VALUE="Name=value"`.
- The config store (`ns3/config-store-module.h`) saves and loads all attribute values to a file (`ns3::ConfigStore::Filename`, `Mode`, `FileFormat`); it documents a run exactly.

## 3. Trace sources and sinks

A trace source is a named hook on an object; a trace sink is a callback you connect to it. Find sources in Doxygen ("TraceSources" section of the class) or with `./ns3 show typeid`.

```cpp
void RxSink(Ptr<const Packet> p, const Address& from)
{
    NS_LOG_INFO(Simulator::Now().As(Time::S) << " rx " << p->GetSize() << " B");
}

void CwndSink(uint32_t oldVal, uint32_t newVal) { /* ... */ }

void CourseSink(std::string context, Ptr<const MobilityModel> m)
{
    Vector v = m->GetPosition();
    // context identifies the node when connected with a wildcard path
}

// Connect without context: the sink gets only the trace arguments
Config::ConnectWithoutContext(
    "/NodeList/1/ApplicationList/0/$ns3::PacketSink/Rx", MakeCallback(&RxSink));

// Connect with context: the first sink argument is the matched path
Config::Connect("/NodeList/*/$ns3::MobilityModel/CourseChange",
                MakeCallback(&CourseSink));

// Directly on an object pointer
Ptr<PacketSink> sink = DynamicCast<PacketSink>(apps.Get(0));
sink->TraceConnectWithoutContext("Rx", MakeCallback(&RxSink));
```

- The sink signature must match the source's callback type exactly (documented as `ns3::Packet::AddressTracedCallback`, `ns3::TracedValueCallback::Uint32`, and so on). A mismatch is a compile error or a fatal error when the callback is connected; copy the signature from Doxygen.
- `Config::Connect*` resolves paths when called, so nodes and devices must exist. Connect after the topology is built, or use `Simulator::Schedule(Seconds(0.001), &ConnectTraces)` when the object appears later (TCP sockets exist only after the connection starts).
- Use `MakeBoundCallback(&Fn, arg1, arg2)` to pass extra arguments such as an output stream. A member function sink uses `MakeCallback(&Class::Method, objectPtr)`.
- `TracedValue<T>` members (congestion window, queue size) call the sink with `(old, new)` on each change; `TracedCallback<...>` members call with the listed arguments.
- Useful sources: `PacketSink/Rx`, `UdpServer/RxWithAddresses`, `UdpClient/Tx`, `PointToPointNetDevice/MacTx|MacRx|PhyTxDrop`, `Queue/Enqueue|Dequeue|Drop`, `TcpSocketBase/CongestionWindow`, `MobilityModel/CourseChange`, `WifiPhy/PhyRxDrop`. Confirm each in the documentation of the version in use.
- The `FileHelper`, `GnuplotHelper` and probes in the `stats` module build time series and files from trace sources without hand-written sinks; check the stats chapter of the manual for their current API.
- Keep sinks cheap. Per-packet sinks with `std::endl` or large `std::map` growth dominate run time in long simulations; buffer output and flush at the end.

## 4. PCAP and ASCII traces

```cpp
PointToPointHelper p2p;
// ... Install ...
p2p.EnablePcapAll("results/run1/p2p");           // one file per device
p2p.EnablePcap("results/run1/p2p-dev", devs.Get(0), true);  // one device, promiscuous

AsciiTraceHelper ascii;
p2p.EnableAsciiAll(ascii.CreateFileStream("results/run1/p2p.tr"));
```

- File names are `<prefix>-<nodeId>-<deviceId>.pcap`. The output directory must exist; ns-3 does not create it. With `./ns3 run --cwd=<dir>` relative prefixes land in that directory.
- Open PCAP files with Wireshark or `tcpdump -nn -r file.pcap`; `tshark -r file.pcap -q -z io,stat,1` gives per-second counts.
- ASCII trace lines start with an event code: `+` enqueue, `-` dequeue, `d` drop, `r` receive. Format details depend on the device type.
- Wi-Fi PCAP needs a radiotap link type for useful dissection: `phy.SetPcapDataLinkType(WifiPhyHelper::DLT_IEEE802_11_RADIO)` before `EnablePcap`.
- Tracing every device in a large scenario creates thousands of files and slows the run. Enable PCAP on the few devices you inspect.
- Cellular modules (lte, nr) do not produce device PCAP files in the same way; they write their own text or SQLite trace files. See [nr-5g-lena.md](nr-5g-lena.md).

## 5. FlowMonitor

FlowMonitor measures per-flow packet counts, bytes, delay and jitter at the IP layer, independently of applications.

```cpp
FlowMonitorHelper fm;
Ptr<FlowMonitor> monitor = fm.InstallAll();     // or fm.Install(nodeContainer)

Simulator::Stop(Seconds(11));
Simulator::Run();

monitor->CheckForLostPackets();
Ptr<Ipv4FlowClassifier> cls = DynamicCast<Ipv4FlowClassifier>(fm.GetClassifier());
for (const auto& [id, st] : monitor->GetFlowStats())
{
    Ipv4FlowClassifier::FiveTuple t = cls->FindFlow(id);
    double dur = (st.timeLastRxPacket - st.timeFirstTxPacket).GetSeconds();
    double mbps = dur > 0 ? st.rxBytes * 8.0 / dur / 1e6 : 0.0;
    double delayMs = st.rxPackets ? st.delaySum.GetMilliSeconds() * 1.0 / st.rxPackets : 0.0;
    std::cout << t.sourceAddress << ":" << t.sourcePort << " -> " << t.destinationAddress
              << ":" << t.destinationPort << " tx=" << st.txPackets << " rx=" << st.rxPackets
              << " lost=" << st.lostPackets << " mbps=" << mbps << " delay_ms=" << delayMs
              << "\n";
}
monitor->SerializeToXmlFile("flowmon.xml", true, true);   // histograms, probes
```

- `FlowStats` fields: `txPackets`, `rxPackets`, `txBytes`, `rxBytes`, `lostPackets`, `delaySum`, `jitterSum`, `timeFirstTxPacket`, `timeLastRxPacket`, `lastDelay`, `minDelay`, `maxDelay`, and drop and forwarding counters.
- Call `CheckForLostPackets()` after the run (and let the simulation continue a little past the last transmission) so in-flight packets are not counted as lost.
- Flows are classified by the 5-tuple. A retransmitting or reordering protocol, a tunnel (the cellular core encapsulates user traffic in GTP-U) or NAT changes what counts as one flow. Install the monitor on end nodes only (`Install(NodeContainer)` with the remote host and the UEs) so core and radio hops are not counted twice.
- Attributes: `DelayBinWidth`, `JitterBinWidth`, `PacketSizeBinWidth`, `FlowInterruptionsBinWidth`, `StartTime`, `MaxPerHopDelay`. Set them with `monitor->SetAttribute(...)` before the run.
- IPv6: use `fm.GetClassifier6()` and `Ipv6FlowClassifier`.
- Mean delay uses `delaySum / rxPackets`; jitter uses `jitterSum / (rxPackets - 1)`. Report the definition used.
- FlowMonitor outputs one value per flow per run. For statistics across replications, write one CSV row per run and analyse in a separate tool (statistics-expert).

## 6. Logging

Logging works only in builds with logs enabled (`default` and `debug` profiles, or `--enable-logs`).

```cpp
NS_LOG_COMPONENT_DEFINE("MySim");                // once per file, outside functions

NS_LOG_INFO("started with " << nUe << " UEs");
NS_LOG_WARN("queue almost full");
NS_LOG_DEBUG("state=" << state);
NS_LOG_FUNCTION(this << arg);                    // inside model methods
```

```bash
NS_LOG="MySim=level_info|prefix_time" ./ns3 run scratch/my-sim
NS_LOG="UdpServer=level_all|prefix_func|prefix_time:UdpClient=info" ./ns3 run scratch/my-sim
NS_LOG="*=level_warn|prefix_node|prefix_time" ./ns3 run scratch/my-sim
```

- Syntax: `Component=flags` pairs separated by `:`; flags are joined by `|`. Levels: `error`, `warn`, `debug`, `info`, `function`, `logic`; the `level_X` forms mean "X and below" (`level_info` includes error, warn, debug and info). `all` / `level_all` enable everything; prefixes: `prefix_func`, `prefix_time`, `prefix_node`, `prefix_level`, `prefix_all`.
- In ns-3.49 the ordering changed: `function` is now the most verbose level, and `level_logic` and `level_debug` no longer include function traces. To get the earlier output use `level_logic|function` instead of the former `level_logic`, and `level_function` instead of the former `level_debug`.
- In code: `LogComponentEnable("UdpServer", LOG_LEVEL_INFO)` and `LogComponentEnableAll(LOG_PREFIX_TIME)`.
- List components with `NS_LOG=` set to a wrong name (the error lists valid names), or search the source for `NS_LOG_COMPONENT_DEFINE`.
- Logging writes to `std::clog` (stderr). Redirect with `2> run.log`.
- Do not place needed side effects in log statements; they disappear in release builds.
- Full `level_all` on a large model produces gigabytes. Enable the one or two components that matter.

## 7. Output hygiene

- Write each run's outputs to its own directory named after the parameters and run number (`results/ue20_rate5_run7/`); never overwrite.
- Write results as CSV or JSON with a header, one file per run or one row per run, with parameters included in the row.
- Keep stdout for progress and results summaries only; send data to files. Always write the full command line, ns-3 version and nr commit with the output (see [reproducible-experiments.md](reproducible-experiments.md)).
- Close or flush `std::ofstream` before `Simulator::Destroy()` returns; data is lost if the program aborts.
- Check for a non-zero exit code: a run that hit `NS_FATAL_ERROR` produces partial files that look valid.
- Use `Simulator::Now().GetSeconds()` for timestamps in output; `Time::As(Time::S)` for printing with units.
