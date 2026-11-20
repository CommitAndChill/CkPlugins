# Packaged late-join profile

On the i9-10900KF, the dominant observable interval was a sustained stream of three downstream datagrams roughly every 33 ms. At 90% occupancy that interval alone lasted 6.9–7.0 seconds on the 10 Mbps link. Its bandwidth usage was about 7%. All ten clients ultimately matched the authority manifest, including every placement and occupant identity.

The measurements cover the November 19 Win64 Development cohort, with separate dedicated server and null-RHI client processes on the same PC, two radius-32 boards of 3,169 cells each, independent 25 ms delays per direction and a 10 Mbps serializer per direction. Each column spans five measured pairs after an excluded warmup. [Per-pair measurements](join_samples.csv) · [Cohort audit](audit-samples.csv)

| Measurement | 50%, 3,168 objects | 90%, 5,704 objects |
| --- | ---: | ---: |
| Client pre-browse initialization to observed open | 423–483 ms | 441–494 ms |
| Client map load from engine log, overlaps connection setup | 81–83 ms | 81–83 ms |
| Client observed open to completed full-manifest construction, p95 (max of five) | 4,077 ms | 7,602 ms |
| Server observed open to reading the client’s hash receipt | 4,365–4,431 ms | 7,879–7,912 ms |
| First upstream receipt at relay to first downstream forward | 52–80 ms | 54–82 ms |
| First upstream receipt to first downstream forward ≥800 wire bytes | 393–452 ms | 410–462 ms |
| Duration of regular traffic before burst, 100 ms bins | 3,800 ms | 6,900–7,000 ms |
| Average downstream rate in regular interval | 0.690–0.694 Mbps | 0.692–0.697 Mbps |
| Complete relay-ingress groups containing exactly three datagrams | 557 of 561 | 1,032 of 1,036 |
| Median group period at relay ingress, spread across pairs | 33.22–33.43 ms | 33.22–33.48 ms |
| First burst bin start to supervisor observing receipt | 242–336 ms | 575–656 ms |
| Last downstream datagram ≥800 wire bytes to supervisor observing receipt | 77–107 ms | 128–154 ms |
| Total downstream modeled IPv4/UDP bytes through supervisor observation | 504,949–505,031 B | 904,976–905,020 B |
| Ideal serial time for those bytes at 10 Mbps | ~404 ms | ~724 ms |

The client duration ends after verifying both boards and constructing a sorted manifest. Hashing that manifest, comparing the server hash and writing the receipt follow the timestamp. The profiler rehashed the actual client and authority files and verified their row counts in all ten cases. The server’s own clock interval includes its polling of that file. The relay uses its validated supervisor cutoff on Windows QueryPerformanceCounter. Its first packet is the first upstream datagram seen by the relay. The elapsed time before that datagram, relative to client browse, has no paired clock marker. The three timelines overlap and their durations cannot be added.

**Where the time goes.** The packet cadence is already present at relay ingress. The relay accepts groups of about three large datagrams spaced ~33 ms apart, then forwards them. A 10 Mbps serializer can send ~41.7 kB in 33.3 ms. The sustained sender traffic consumes about 2.9 kB in that period. The final burst begins much later as density increases. The server logs confirm that the packaged run used Iris and negotiated 1,250,000 B/s. The registered engine defaults its ordinary replication writer cap to three packets per batch and further limits the allocation by queued-bit headroom. The writer separately permits more data for huge objects and certain attachments. This explains why testing the packet cap is the first discriminating experiment. These packet logs alone cannot identify the limiter or label burst content. DataStreamChannel.cpp (`Engine/Source/Runtime/Engine/Private/Net/Experimental/Iris/DataStreamChannel.cpp:322` in the engine checkout) · ReplicationWriter.cpp (`Engine/Source/Runtime/Net/Iris/Private/Iris/ReplicationSystem/ReplicationWriter.cpp:4415` in the engine checkout)

**Verification boundary.** The relay records all traffic. Its ≥800 B cutoff distinguishes large packets only by size. The last-large-packet interval includes any remaining network work, client verification, receipt I/O and supervisor polling. The fixture enumerates all piece actors each time it tests usability and checks accepted bindings, placement lookups, cells and handles before constructing the sorted manifest. Its repeated polling may itself consume CPU. The endpoint logs supply no exclusive time for projection materialization, binding resolution or verification. Retain the full verifier and time it separately. [CkHexDenseAcceptance.cpp](../../../../../Plugins/CkTests/Source/CkTests/Private/HexGrid/CkHexDenseAcceptance.cpp#L204)

## Temporary packet-cap experiment

Two further 90% packaged runs on this PC changed the server's ordinary Iris packet cap. Server console readback confirmed 3 and 12. Each client reproduced all 5,704 rows of its own authority manifest and both roles completed teardown. The probes held the emulated link and negotiated speed fixed. One observation per setting supports attribution and leaves release qualification open. [Probe audit](join_cap_pair.csv) · Reproducible calculation (source workstation, `join_cap_pair.py`)

| Measurement | Cap 3 | Cap 12 |
| --- | ---: | ---: |
| Client observed open to verified | 7,599.94 ms | 1,891.19 ms |
| Client pre-browse to verified | 8,024.52 ms | 2,381.85 ms |
| Total downstream modeled bytes through receipt observation | 905,161 | 904,479 |
| Longest run of ingress groups exactly equal to cap | 205 groups of 3 | 45 groups of 12 |
| Median period within that run | 33.25 ms | 33.28 ms |
| Mean forwarding rate in full 100 ms bins inside that run | 0.694 Mbps over 6.7 s | 2.774 Mbps over 1.3 s |
| First ≥20 kB bin from first upstream packet | 7.4 s | 0.5 s |
| Last ≥800 B downstream packet to supervisor receipt observation | 159 ms | 93 ms |

The fourfold increase in cap produced fourfold throughput during the regular cadence, with a 5.71 s reduction in observed join time and 682 B less total downstream traffic. The cap-12 run still missed the 1 s target. Its early high-volume burst was followed by a long twelve-packet cadence. Randomly generated identities and burst ordering differed between the two runs. Actor creation versus board baseline, client CPU and reliable-dependency waits still require independent attribution. Both probes returned successful fixture and relay exits. Each had 201 diagnostic lines per role, rejected offline inspection, and endpoint-unreachable notices after the verified cutoff. The whole-flow clean gate remains open.

**Next decision gate.** Repeat the cap comparison at both densities and add an already-connected peer carrying ordinary traffic. Record the per-frame send budget, packet-window occupancy, queue saturation, established-peer latency and hitches before selecting a persistent policy. Decode the preserved per-role NetTrace traces for actors, identities and board baseline bits. If the content trace cannot identify an event, retain the unknown bytes. Gather client CPU spans for receive-to-board-ready, pending-to-bound transitions, first all-bound and verifier CPU on a common endpoint clock. Compare production and fixture costs separately before proposing any materialization or wire-format change.

**Reproduction.** Run `python docs/campaigns/hex-grid/evidence/phase-8-profiling/join_profile.py` from this checkout. The script reads the qualification cohort’s endpoint logs, verified cutoff, packet journal and two manifests per pair. Downstream bytes are UDP payload plus 28 B of modeled headers. It bins forwarded bytes into 100 ms windows from the first upstream datagram, starting the regular interval at the first bin with ≥6,000 B and ending at the first bin with ≥20,000 B. These diagnostic boundaries have 100 ms resolution. It groups the corresponding ingress packets using ≥10 ms of silence and excludes the first and last groups to avoid bin truncation. The reference transfer times serialize *all* bytes through the supervisor cutoff, including handshake and control packets. They describe this captured volume and cannot be subtracted from the client timer to infer a CPU budget. Analysis script (source workstation, `join_profile.py`)
