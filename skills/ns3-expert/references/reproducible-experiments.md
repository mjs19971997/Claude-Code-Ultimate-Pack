# Reproducible ns-3 Experiments

Seeds, run numbers and streams in ns-3, how to produce independent replications, how to script a parameter sweep, and what to record so a result can be regenerated later. RNG behaviour checked against the ns-3.49 manual source (`random-variables.rst`) and `rng-seed-manager.cc` in 2026-10. Choosing the number of replications, confidence intervals and warm-up deletion belong to statistics-expert.

## Contents

1. [How ns-3 randomness works](#1-how-ns-3-randomness-works)
2. [Independent replications](#2-independent-replications)
3. [Streams and common random numbers](#3-streams-and-common-random-numbers)
4. [Sources of non-determinism](#4-sources-of-non-determinism)
5. [A sweep script](#5-a-sweep-script)
6. [What to record](#6-what-to-record)
7. [Checks before trusting results](#7-checks-before-trusting-results)

## 1. How ns-3 randomness works

- ns-3 uses the MRG32k3a generator. The manual gives 1.8e19 independent streams, 2.3e15 substreams per stream, and a period of 7.6e22 per substream.
- Two global values control the sequence: `RngSeed` (default 1) and `RngRun` (default 1). With no change, every execution of the same binary and arguments gives identical results.
- The seed selects the generator state; the run number selects the substream. Substreams do not overlap; different seeds carry no such guarantee.
- Each random variable object (`UniformRandomVariable`, `ExponentialRandomVariable`, models inside the wifi, lte and nr modules) is bound to one stream, set by the `Stream` attribute. The default `-1` means automatic assignment; automatic streams are handed out in sequence as the objects are set up (the manual describes this as first use; the code does it when the object's stream is initialised), so the mapping depends on creation order. A non-negative `Stream` pins the object to that stream (user indices are 0 to 2^63-1; automatic ones use the other half).
- `RngSeedManager::SetSeed(uint32_t)` and `SetRun(uint64_t)` write the globals `RngSeed` and `RngRun`. Call them before creating any random variable: the seed and run are read when a variable's stream is set up.
- `RngSeedManager::GetNextStreamIndex()` returns the next automatic index; `ResetNextStreamIndex()` resets it.

## 2. Independent replications

Fix the seed, vary the run number. The manual states this explicitly: use the substream capability for multiple independent runs, because there is no guarantee that streams from two different seeds will not overlap.

```bash
# Equivalent ways to select run 3
./ns3 run scratch/my-sim -- --RngRun=3
NS_GLOBAL_VALUE="RngRun=3" ./ns3 run scratch/my-sim
./ns3 run scratch/my-sim --command-template="%s --RngRun=3"
```

In code, only when the run number is not meant to come from the command line:

```cpp
CommandLine cmd(__FILE__);
cmd.Parse(argc, argv);
// RngSeed and RngRun are now whatever --RngSeed / --RngRun set; do not call SetRun here
// unless you want to override them.
```

- `--RngRun` and `--RngSeed` need no `AddValue`; they are global values. Calling `RngSeedManager::SetRun(k)` after `Parse` silently overrides the command line; an experiment script then runs the same replication N times.
- Choose a set of run numbers up front (1 to N) and store them with the results. Do not choose seeds by wall-clock time: the experiment cannot be repeated.
- Replications are independent only if every random source is driven by the ns-3 generators. See [Sources of non-determinism](#4-sources-of-non-determinism).
- Changing the seed as well as the run is legitimate for a second, separate campaign. Do not mix seeds within one set of replications.
- The initial transient and run length are modelling choices; decide them with a pilot run and statistics-expert before running a campaign.

## 3. Streams and common random numbers

Automatic stream assignment depends on the order in which objects are created and first used. Adding a node or reordering helper calls changes which stream every later object receives, so two configurations that differ in one detail do not share randomness. For a paired comparison (variant A versus variant B under the same traffic and mobility), pin the streams.

```cpp
int64_t stream = 100;                       // first stream index for this scenario
stream += mobility.AssignStreams(ueNodes, stream);
stream += internet.AssignStreams(allNodes, stream);
stream += onoff.AssignStreams(sourceNodes, stream);   // application helpers
stream += wifi.AssignStreams(devices, stream);        // device helpers that offer it
NS_LOG_INFO("streams used: " << stream - 100);

Ptr<UniformRandomVariable> x = CreateObject<UniformRandomVariable>();
x->SetStream(5);                            // pins a user-level variable
```

- Helpers that create random objects expose `AssignStreams(NodeContainer or NetDeviceContainer, int64_t firstStream)` and return the number of streams used; chain the return values as above so ranges never overlap.
- Give each independent source of randomness its own range: traffic, mobility, radio channel, scheduler. Leave gaps (for example blocks of 100 or 1000) so one source can grow without colliding with the next.
- `Stream` is an attribute of every random variable, so it can also be given in a `StringValue` such as `"ns3::UniformRandomVariable[Min=0|Max=1|Stream=7]"`.
- The nr module provides one call, `NrHelper::AssignStreams` with a parameter struct, that assigns all nr, scenario, beamforming and optional EPC streams; see [nr-5g-lena.md](nr-5g-lena.md).
- Common random numbers reduce variance only when the compared variants consume streams in the same pattern. Verify by checking that a neutral change (a log statement, an extra disabled trace) leaves results identical.

## 4. Sources of non-determinism

- `std::rand`, `rand()`, `std::random_device`, `std::mt19937` seeded by time, `time(nullptr)`, `std::chrono` clocks in model logic: replace with ns-3 random variables.
- Iterating `std::unordered_map` or `std::unordered_set` with pointer keys or with implementation-defined hashing can change order between builds. Use ordered containers or sort before iterating when order affects events.
- Uninitialised variables: build once with `--enable-sanitizers` and run the scenario.
- Reading input files that change between runs (mobility traces, configuration) without versioning them.
- Events scheduled for identical times: ns-3 orders them by insertion; code that depends on tie ordering between nodes is brittle after refactoring.
- Floating-point results depend on compiler, optimisation flags (`-march=native` in the `optimized` profile) and library versions. Compare numbers across machines only with the same toolchain; use tolerance when comparing otherwise.
- Real-time or emulation modes (`RealtimeSimulatorImpl`, TAP/EMU devices) are not reproducible.
- Running many independent processes at once does not change any result, as long as each writes to its own directory.
- Cross-process sharing: never let two runs write the same output filename (`flowmon.xml` in a shared directory).

## 5. A sweep script

Build once, then launch each run in its own directory with its own log and exit status. The script is a template; adapt the program path and argument names.

```bash
#!/usr/bin/env bash
# sweep.sh - run PROG for every (rate, run) pair; NS3_DIR points at the ns-3 checkout
set -euo pipefail

NS3_DIR=${NS3_DIR:?set NS3_DIR to the ns-3 checkout}
PROG=${PROG:-scratch/my-sim}
OUT=${OUT:-$PWD/results}
RUNS=${RUNS:-10}
JOBS=${JOBS:-4}
RATES=(2Mbps 5Mbps 10Mbps)

mkdir -p "$OUT"
( cd "$NS3_DIR" && ./ns3 build "$PROG" )

# Record the environment once per campaign
{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "ns3_commit=$(git -C "$NS3_DIR" rev-parse HEAD)"
  echo "ns3_describe=$(git -C "$NS3_DIR" describe --tags --always)"
  echo "ns3_version=$(cd "$NS3_DIR" && ./ns3 show version)"
  if [ -d "$NS3_DIR/contrib/nr/.git" ]; then
    echo "nr_commit=$(git -C "$NS3_DIR/contrib/nr" rev-parse HEAD)"
  fi
  echo "compiler=$(c++ --version | head -n 1)"
  echo "host=$(uname -srm)"
  echo "prog=$PROG runs=$RUNS rates=${RATES[*]}"
} > "$OUT/manifest.txt"

run_one() {
  local rate=$1 run=$2
  local dir="$OUT/rate${rate}_run${run}"
  mkdir -p "$dir"
  if ( cd "$NS3_DIR" && ./ns3 run --no-build "$PROG" --cwd "$dir" -- \
         --RngRun="$run" --rate="$rate" --simTime=20s ) \
       > "$dir/stdout.log" 2> "$dir/stderr.log"; then
    echo ok > "$dir/STATUS"
  else
    echo failed > "$dir/STATUS"
  fi
}

for rate in "${RATES[@]}"; do
  for run in $(seq 1 "$RUNS"); do
    while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do wait -n || true; done
    run_one "$rate" "$run" &
  done
done
wait

grep -L '^ok$' "$OUT"/*/STATUS || true     # lists runs that did not finish
```

- Keep `JOBS` at or below the number of physical cores and below what RAM allows; nr and wifi scenarios can use several GB per process.
- `--no-build` plus a single prior `./ns3 build` prevents parallel runs from racing on the build directory.
- On a cluster, a job array maps `SLURM_ARRAY_TASK_ID` (or the scheduler's equivalent) to `--RngRun`; one run per array task, same binary, shared read-only build directory, per-task output directory.
- Programs write results to the working directory (`--cwd`), not to absolute paths hard-coded in the source.
- Restarting: skip directories whose `STATUS` is `ok` so an interrupted campaign continues without redoing runs.
- Aggregate afterwards in a separate step (pandas, R). The aggregation script reads `result.csv` from each run directory, never stdout.

## 6. What to record

Store, with every result set:

| Item | How to get it |
|---|---|
| ns-3 release or commit | `git describe --tags --always`, `./ns3 show version` |
| Contrib module commits (nr, others) | `git -C contrib/nr rev-parse HEAD` |
| Any local patch | `git diff > local.patch`; store it, or commit to a branch |
| Build profile and enabled features | `./ns3 show profile`, `./ns3 show config` |
| Compiler and OS | `c++ --version`, `uname -a`, container image digest |
| Full command line, including `RngSeed` and `RngRun` | The script itself, copied into the output directory |
| Attribute defaults | Config store dump (`ns3::ConfigStore::Mode=Save`) or the program's own parameter print |
| Input data versions | Checksums (`sha256sum`) of traces, maps, configuration files |
| Dates and wall-clock time per run | Script manifest |

- Commit the scenario source and scripts to Git before the campaign and put the commit hash in the manifest. A dirty tree makes the hash meaningless; check `git status --porcelain` in the script.
- Print the effective parameters at the start of every run (`std::cout` or a `params.json`); this protects against a script and a program disagreeing on defaults.
- A container image with a fixed compiler and the ns-3 checkout is the most robust form of "environment"; store its digest, not only its tag.
- Archive the raw per-run outputs; derived tables and figures should be regenerable from them with one command.

## 7. Checks before trusting results

1. Same seed and run, same binary, twice: outputs must be byte-identical (`cmp a/result.csv b/result.csv`). If not, find the non-determinism first.
2. Different `RngRun`: outputs must differ. If every replication is identical, the run number is overridden (`SetRun` in code) or no random variable is in use.
3. Same scenario, `default` profile and the sweep profile: numerical agreement (modulo floating-point noise) confirms no logic hides inside `NS_ASSERT`/`NS_LOG`.
4. Check conservation: packets sent = received + dropped (queue, radio, buffer overflow) for a short run. A mismatch means a trace or classification error.
5. Check the warm-up: plot the metric over time for one run and confirm the measurement window starts after the transient.
6. Look at one run in detail (a PCAP or a log) to confirm that the traffic and topology are what was intended before launching the campaign.
7. Keep a failing-run list: a campaign with silently missing runs biases the average (for example, only short, successful runs survive).
