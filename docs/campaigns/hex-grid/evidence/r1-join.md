# R1 late join on the qualification workstation

**The temporary cap of 12 reduced join time in all eight matched comparisons. All joins still exceeded 1,000 ms.** At cap 12 the two board placement arrays finished decoding in under 181 ms at 50% occupancy and under 347 ms at 90%. Object binding identities continued arriving past the budget at both densities. These comparisons change neither project transport defaults nor the release verdict.

## Repeated packaged joins

Four counterbalanced blocks tested each density and cap. Each cell also has one net-only control and one separate fully trace-off control, on the same staged pair and emulated link. The profiled columns report the mean and observed range of four measured processes per cell. The control values are individual observations. [Cohort ledger](r1-cohort.csv)

| Occupancy / cap | Open to verified, mean ms | Profiled range, ms | Net only, ms | Fully trace off, ms | Forwarded wire bytes through receipt |
|---|---:|---:|---:|---:|---:|
| 50% / 3 | 4,079.43 | 4,063.23–4,090.21 | 4,083.61 | 4,059.99 | 504,954–505,047 |
| 50% / 12 | 1,115.75 | 1,114.36–1,117.75 | 1,113.65 | 1,112.66 | 504,999–505,058 |
| 90% / 3 | 7,598.32 | 7,585.01–7,610.88 | 7,582.46 | 7,417.01 | 904,978–905,182 |
| 90% / 12 | 1,974.08 | 1,966.38–1,984.68 | 1,982.90 | 1,934.30 | 904,288–904,557 |

Within matched blocks the latency reduction was 2,945–2,974 ms at 50% and 5,619–5,629 ms at 90%. During the longest steady runs of exact-cap packet groups, downstream throughput was approximately 0.69–0.70 Mbps at cap 3 and 2.77–2.81 Mbps at cap 12. End-to-end modeled downstream volume changed by less than 0.1% between caps within each matched block. Results in net-only and trace-off controls retained the same direction and release-budget misses. The single trace-off controls cannot isolate a stable profiling-overhead percentage.

The admission audit preserved two attempts with out-of-bounds relay forwarding and two otherwise relay-valid attempts that overlapped an unrelated build. Their replacements ran after the workstation guard cleared. All sixteen profiled and four net-only samples in the tables passed the interval relay audit. Each client matched all 3,168 / 5,704 distinct authority manifest rows at its density.

## Which dependency finished last

Each logical receive timestamp comes from the end of processing an incoming client packet. Bounds below incorporate clock-placement uncertainty and the full four-run spread. The first required read was within approximately 10 ms of the fixture's first observed open in all four cells. The packet-processing span and the final interval are disjoint.

| Occupancy / cap | Last board array, ms from open | Last identity, ms from open | First to last typed read, ms | Last typed read to verified, ms | Inferred unsuccessful polls |
|---|---:|---:|---:|---:|---:|
| 50% / 3 | 4,008–4,049 | 3,957–3,997 | 4,016–4,042 | 38–61 | 1,896–3,451 |
| 50% / 12 | 163–181 | 1,084–1,107 | 1,092–1,099 | 11–31 | 349–402 |
| 90% / 3 | 7,491–7,531 | 7,107–7,138 | 7,500–7,524 | 77–97 | 3,320–4,399 |
| 90% / 12 | 309–347 | 1,928–1,958 | 1,935–1,950 | 23–43 | 440–517 |

Every capture contained two client-side logical board array reads and one identity GUID read per expected object. At 50% the two arrays totaled 1,150,018 logical bits and the identity GUID fields totaled 408,672 bits. At 90% the totals were 2,070,586 and 735,816 bits respectively. These are field scopes at the serialization layer. The complete enclosing serialized values, actor creation references, and wire traffic use different denominators. At cap 12 the last identity was already late before the final verification interval began. Optimizing only the work after the last packet cannot close the miss. [Four control traces with enclosing typed values and actor creation](r1-control-typed.csv)

## Repeated client frame tails

Each entry is the range across the four runs of a per-run statistic. This uncapped null-RHI client does not qualify the rendered 1080p60 gameplay-frame budget.

| Occupancy / cap | p95 frame, ms | p99 frame, ms | Worst frame, ms | Frames >16.67 ms |
|---|---:|---:|---:|---:|
| 50% / 3 | 1.71–7.33 | 7.44–11.68 | 63.66–68.95 | 2–4 |
| 50% / 12 | 21.61–22.43 | 23.60–27.83 | 48.99–50.10 | 30–31 |
| 90% / 3 | 4.30–7.70 | 9.17–9.97 | 106.65–110.25 | 4–5 |
| 90% / 12 | 24.39–25.56 | 27.75–34.58 | 78.94–94.00 | 49–50 |

Cap 12 produced fewer frames overall and many more frames above 16.67 ms. Its worst single frame was shorter in every R1 pair. The earlier isolated 192 ms maximum did not recur. A transport decision should use frame-time distributions, endpoint readiness and existing-client fairness together.

## Residual client work after the last required typed packet

One first-block client at each density and cap was replayed from CPU event batches. The interval ends at the earliest possible verification endpoint given the release stopwatch and game-frame bounds. The adjacent uncertainty window is exported separately. Values below are wall milliseconds charged to innermost named batch scopes and uninstrumented descendants.

| Density / cap | Minimum interval still on the clock | Largest named time in that interval |
|---|---:|---|
| 50% / 3 | 38.95 ms | ReplicatedFragments dispatch 21.67 ms, EntityScript spawn request 9.21 ms |
| 50% / 12 | 15.30 ms | Generic ticker 5.33 ms, EntityScript spawn request 2.73 ms, CreateObject 1.99 ms |
| 90% / 3 | 80.13 ms | ReplicatedFragments dispatch 43.54 ms, generic ticker 19.22 ms |
| 90% / 12 | 26.42 ms | Generic ticker 19.66 ms |

In these four clients, the final interval is tens of milliseconds. While each joining client is still processing packets, local execution already overlaps delivery. Adding the full client CPU total to a simulated transfer time would double-count that overlap.

### Successful manifest verification

A focused replay found exactly two class scans in the phase 6 ticker before its completion log for each representative client. The success path requires both scans. The enclosing ticker start and first scan bound entry to Verify. The phase 5 ticker start and log bound stopwatch start, which fixes the end of Verify within 0.025–0.033 ms using the recorded duration. These bounds include all work of the successful Verify call. Previously failed polls remain inside the end-to-end release clock.

| Occupancy / cap | End of last typed packet to verified, ms | Successful Verify duration, ms |
|---|---:|---:|
| 50% / 3 | 55.2567–55.2897 | 18.3764–18.4276 |
| 50% / 12 | 30.3264–30.3515 | 20.4886–20.5303 |
| 90% / 3 | 95.3530–95.3800 | 34.6852–34.7297 |
| 90% / 12 | 41.5589–41.5842 | 34.9944–35.0364 |

Verified query results certify complete binding by the successful manifest read. The actual first usable instant and cost of each prior failed poll would require a narrower diagnostic scope. [Ticker and class-scan evidence](r1-join-final-verify.csv)

## What the clocks measure

The fixture used the same staged Win64 Development dedicated server and null-RHI client binaries, i9-10900KF workstation, two radius-32 boards with 3,169 cells each, and per-direction 25 ms propagation and 10 Mbps serialization. Each run used fresh processes and isolated run IDs. An independent replay checked each server's Iris CVar readback, negotiated rate, traced channels, row count, byte-identical client/authority manifests, per-role SHA-1 receipts, teardown and relay audit. Endpoint manifests use fresh identities per run. The packet pacing comparison changes only the server's temporary cap within an instrumentation condition. The trace-on and net-only rows report separate instrumentation conditions.

* **Observed open and verified.** The fixture starts its monotonic stopwatch on the first qualifying tick with an open connection and begun-play client world. It stops after both boards and every object pass their public lookups and the sorted manifest is constructed. Comparison, hashing and receipt I/O follow. The supervisor clock ends later, after detecting and validating the receipt. Supervisor relay wire bytes include UDP payload plus 28 modeled IPv4/UDP header bytes per datagram through that cutoff. The audited link is emulated loopback.
* **Typed packet reads.** The analyzer decodes UE protocol-7 event definitions, game-thread records, NetTrace names and variable-length packet content. For the sole incoming connection it groups logical field scopes with their subsequent incoming PacketEvent. The engine emits that marker at the end of receive processing. Reassembled huge-board values can be attached to the packet that completes reassembly. The measurement does not localize the UDP datagram containing the first board bits. It also cannot identify the instant that client ECS binding commits. The identity field and each board's placements array have distinct serialization scopes. Placement IDs and occupant binding IDs are reported as nested fields; adding them to the array would double-count them.
* **Clock alignment and polls.** The client's phase 5 and phase 6 log events carry their own QPC from the originating CkHexDenseAcceptance log point. We verified their phase arguments, exact game frame, modulo-1,000 text-log frame number and supervisor UTC↔QPC anchor. The start lies after its frame opens and before phase 5 is logged. The measured elapsed interval and the corresponding complete frame and phase 6 log bound the true verification endpoint. A negative lower bound means the first logical read can precede the first qualifying open tick. Uninstrumented controls have no frame bracket. Their clock offsets from text log phase 5 are estimates. Under the continuous world, open driver and single zero-delay core ticker, the number of unsuccessful polls is inferred as the successful frame index minus the open frame index minus one. Exact per-poll CPU time and earliest possible public usability within the successful frame remain unresolved.
* **Client frame tails.** Per-run nearest-rank p95/p99 and maximum cover all complete frames from the open frame through the verification frame. The last complete frame may also include hash comparison and receipt I/O. Frame time includes waits and unlabelled work, and this uncapped client can produce thousands of small frames. The separately reported worst frame and counts exceeding 16.67 ms and 50 ms retain stalls hidden by a per-frame percentile.
* **CPU attribution.** For the first admitted block of each density/cap cell, the CPU replay clips the innermost active GameThread EventBatchV3 scope to QPC intervals. From the phase 5 marker to the end of the last required typed packet, from that marker to earliest possible verification, and across the narrow verification-boundary uncertainty interval, these durations sum to the wall interval exactly. Unscoped work, OS scheduling and uninstrumented descendants cannot be identified further. The shared FTSTicker::Tick scope includes multiple ticker instances and unlabelled descendants, including fixture work. The uninstrumented successful Verify can be bounded by its mandatory class scans. Exact per-poll self time, hex baseline apply, last-bind commit and the first successful public query remain unresolved. Values from different roles and overlapping windows cannot be summed.
* **Admission and release.** Tests here are single-client diagnostics. Four matched trace-on repeats per cell characterize reproducibility. Reported ranges and averages are diagnostics. Release qualification still calls for the original fresh-process p95 gate. The known offline inspector refusal, startup diagnostics and post-receipt endpoint-unreachable events are carried forward from the receipts. Spillover, release memory ownership and an established client's fairness remain outside these R1 measurements.

## Reproduction

From the checkout root, run the Python scripts below after the selected cases finish. The first audit checks stage paths, trace modes, log clock anchors, manifest hashes, all typed counts, packet ordering and closure of the relay interval. It records rejected or contaminated runs separately. The CPU exporter reuses the restore team's CPU event-batch decoder and reconciles every exported interval to its QPC boundaries.

~~~text
python docs/campaigns/hex-grid/evidence/r1-join-audit.py
python docs/campaigns/hex-grid/evidence/r1-join-window.py
python docs/campaigns/hex-grid/evidence/r1-join-verify.py
~~~

[Per-run timings, pacing, frame tails and polls](r1-join-runs.csv) · [All client field read bounds](r1-join-fields.csv) · [Per-cell summaries](r1-join-summary.csv) · [Excluded attempts](r1-join-rejections.csv) · [Four client CPU windows](r1-join-client-window.csv) · Receive loop (`Engine/Source/Runtime/Engine/Private/NetConnection.cpp:3593` in the engine checkout) · [Fixture](../../../../Plugins/CkTests/Source/CkTests/Private/HexGrid/CkHexDenseAcceptance.cpp#L353)
