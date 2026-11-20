# Packaged game-thread timing at 90% occupancy

The primary server rebuild frame took **1,174.27 ms**. Three sibling scopes under the core ticker accounted for 794.1 ms in the ECS scheduler, 245.6 ms in post-construction, and 91.9 ms in actor spawning. Within the scheduler branch, 5,706 entity-script spawn requests took 725.0 ms inclusive and 460.1 ms exclusive. Their CreateObject child took 167.5 ms inclusive and 138.4 ms exclusive. Within post-construction, BeginPlay on 5,704 mixed-grid piece actors took 240.5 ms inclusive, including 91.2 ms of entity creation requests. Further subdivision of the 460.1 ms requires finer scopes around the spawn handler, including the bridge and construction operations. [Frame 362 call tree, nodes ≥10 ms inclusive](cpu-server-rebuild.csv)

The same instrumented server spent 2,022.31 ms from load request to verified manifest. The two adjacent resolver and rebuild-complete log entries are 1,181 ms apart, in engine frames 361 and 363. Frame 362 lies between these markers. Elapsed time in a game-thread scope includes its uninstrumented descendants. “Exclusive” subtracts named child scopes. Nested inclusive rows overlap. Neither timer directly measures instructions executed on-core.

## Client interval

One run each at Iris caps 3 and 12 on the same i9-10900KF workstation, under the same RTT and bandwidth settings and with two radius-32 boards and 5,704 occupants. The cap-12 run recovered 5,709 ms of open-to-manifest latency. Its 1,891 ms still exceeds the 1,000 ms p95 target on this single observation, and its largest observed frame was longer. Repeated paired runs must qualify both latency and the frame-time distribution. [Pair and relay evidence](join.md)

| Measurement | Cap 3 | Cap 12 |
|---|---:|---:|
| Open to verified manifest, ms | 7,599.94 | 1,891.19 |
| Inclusive frame indices | 1673–5389 | 1533–1743 |
| Number of frames | 3,717 | 211 |
| Start of first to end of last frame, ms | 7,621.28 | 1,916.44 |
| Sum of game frame durations, ms | 7,599.70 | 1,914.92 |
| Longest game frame, ms | 105.98 | 192.15 |
| Core ticker exclusive, ms | 1,977 | 151 |
| Transform SyncFromActor ForEachEntity exclusive, ms | 461 | 27 |
| Scheduler EmptyViewCheck exclusive, ms | 242 | 21 |
| EntityScript SpawnEntity exclusive, ms | 216 | 213 |
| EntityScript SpawnEntity CreateObject exclusive, ms | 178 | 134 |
| Iris ReplicationReader ReadObjects exclusive, ms | 156 | 158 |
| ReplicatedFragments Dispatch exclusive, ms | 134 | 175 |

The faster transfer ran through fewer uncapped client frames. The ticker includes unlabelled work, including the fixture's readiness polling. Its inclusive or exclusive time cannot isolate Verify. Spawn and Iris reader work persisted at the higher cap. The cap-12 peak frame 1638 charged 50.5 ms exclusive to replicated fragment dispatch. The stock client's two largest frames charged 42.9 and 44.2 ms exclusive to that dispatcher. The trace does not distinguish individual hex board applies within that scope. Instrument the dispatcher’s payload-level work, object spawn, and manifest polls before changing their behavior. [Exported exclusive timers, up to 60 per capture](cpu-client-timers.csv)

## Reproducing the export

Inputs are under Saved/Automation/HexPhase8. Each recorded packaged process used net,cpu,frame,bookmark,log tracing and named events. The logs’ bracketed frame counters wrap at 1,000. Match the phase 5 and 6 messages to the frame times by anchoring the supervisor’s observedUtc to its cutoffPerfCounter in measurement-cutoff.json. The frame events use the same 10 MHz Windows performance counter. In the stock client this identifies 1673 and 5389. With cap 12 it identifies 1533 and 1743. The last selected frame ends approximately 29 and 33 ms respectively before the supervisor notices the receipt. Phase transition logs and whole-frame endpoints bracket the stopwatch, so these ranges include small amounts of work on either side of the measured interval. The offline analyzer's total game frame counts match decoded frame marker counts (984 server, 6,714 stock client, 3,023 cap-12 client).

Run the project CkInsightsAnalyzer offline commandlet using -run=CkInsightsAnalyzer -trace=<absolute utrace> -frames=<inclusive range> -depth=full -timertop=60 -json -output=<absolute output>. The server export used -frames=361-363 and -timertop=45. Under profile-cap3 use server-rebuild.json and client-join.json. Under profile-cap12 use client-join.json. For the server CSV take multiFrame.hotFrames frameIndex=362 and recursively traverse callTree. For each client's CSV multiply each timer's avgExclusiveMs and avgOuterInclusiveMs by frameCount. The JSON rounds the average to 0.001 ms, so total rounding error can reach 1.86 ms (stock) or 0.11 ms (cap 12) per timer. Per-frame exclusive coverage error was below 0.000001 ms throughout both client intervals and the server rebuild frame.

| Trace | SHA-256 |
|---|---|
| Stock server cb0597c0549e40a5bafa9f0a45a7ea2e | ef8444b3012e146e393428c9f86279bf0fbfea22b6f71085f576bd0228f8a0dc |
| Stock client cb0597c0549e40a5bafa9f0a45a7ea2e | eebd121f12e8413ab27b34ca14372a03277f5e743c632178e78c48771e3bed04 |
| Cap-12 client 06c90f737e8e48199287d22bcd884844 | be3c1bd0382ce3648bd83919e33d61c26ac70a125c7d14ce555467d1180feb99 |

The analyzer wrote all three JSON reports and logged invalid memory tags during trace analysis. The commandlets returned failure. Only reconciled game-thread timing is used here. Memory attribution and workers without timelines remain unverified. The existing inspector rejection and packaged runtime diagnostics remain open. Release acceptance requires repeated qualifying runs.
