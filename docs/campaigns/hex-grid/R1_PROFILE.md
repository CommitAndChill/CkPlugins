# R1 — authority restore and late-join attribution

## Measurement contract

Win64 Development packaged Game and dedicated Server on the i9-10900KF workstation. Each fresh process pair ran two radius-32 boards with 3,169 cells each, mixed square/hex actor-backed pieces and 3,168 or 5,704 distinct occupied objects. The server completed the full save, world travel and public manifest check before the client connected. The client verified stable IDs, live occupants and both lookup directions against the authority manifest. The release clocks are authority load request to verified state (250 ms p95) and first observed open to verified client state (1,000 ms p95). The harness also retains the client's pre-browse clock.

The A/B factor was the server process's ordinary Iris writer packet cap, 3 or 12. Both values were read back in each server log. The relay modeled 25 ms propagation each way and independent 10 Mbps serialization. Each density has paired, order-reversed profiled samples and separate controls. Frame tail statistics belong to individual join windows. Stopwatch results from these diagnostic cohorts do not replace the release p95.

The primary comparison requires a matching manifest, complete workload and a scored relay window through the supervisor's receipt. The supervisor reads and hashes the manifest after client verification. A delivered datagram on this loopback link, the end of its processing in the engine, an applied hex payload and the first public usable state are distinct boundaries.

## Outcome

**R1 profiling completed. Phase 8 remains on hold.** Twenty-four admitted server/client pairs comprised four CPU+NetTrace repeats, one NetTrace-only control and one capture-disabled control per density and cap. Another four attempts were retained outside the primary comparison. All 24 reproduced both budget misses and verified their own exact server/client manifests.

| Occupancy | Cap | Restore, profiled median | Join, profiled median (range) | Restore / join, capture disabled |
|---|---:|---:|---:|---:|
| 50% | 3 | 1,168 ms | 4,082 ms (4,063–4,090) | 1,136 / 4,060 ms |
| 50% | 12 | 1,141 ms | 1,115 ms (1,114–1,118) | 1,093 / 1,113 ms |
| 90% | 3 | 2,037 ms | 7,599 ms (7,585–7,611) | 1,885 / 7,417 ms |
| 90% | 12 | 2,019 ms | 1,973 ms (1,966–1,985) | 1,947 / 1,934 ms |

The capture-disabled runs preserve the same admission checks and relay. With one control per setting, the differences establish sensitivity and reproduce the misses. They cannot estimate the overhead distribution. The server restored before the client connected, so a restore-time difference between packet caps has no demonstrated causal interpretation. One admitted 90% cap-3 restore took 2,514 ms and remains in the sample.

## Restore

The two detailed cap-3 samples cover every stage between saved table provenance and ready, with trace markers on the server's own clock. At 50% / 90% occupancy, entity rebuild took 585 / 1,184 ms. Map travel took 128 / 206 ms. The post-stamp enqueue interval took 76 / 128 ms, enqueue to quarantine lift 76 / 145 ms and lift to drain declaration 73 / 126 ms. The hydration dispatcher accounts for 66 / 128 ms in the middle interval. In the following interval hex publication accounts for 15 / 27 ms. Both traces distinguish the two board-apply rows by their placement births. Each board row created 1,584 / 2,852 placement entities, while every identity row created zero. The two board rows together took **48.8 / 98.1 ms**, all identity rows **20.5 / 36.6 ms**, and the remaining interval **6.7 / 10.4 ms**. These disjoint totals include dispatcher overhead and descendants. The board rows ran last even though they came first in the saved table. On the earlier enqueue path, identity work was bounded to 25.3–25.4 / 39.6–39.7 ms. Board-only bounds were wider because the orphan census shares its first boundary. A further 62 / 60 ms of named GameThread idle occurred while observing convergence. Reducing that entire wait would leave most of the overrun.

Both detailed authority traces contained exactly the two class-iterator starts required by one successful public manifest check. This rules out a failed verifier poll in either detailed restore. Using the trace and role log alone, the successful check took between 23–34 ms and 40–67 ms respectively. Verification is measurable and belongs inside the release clock. It accounts for a small fraction of the miss. [Authority waterfall and boundary proof](evidence/r1-restore.md) · [Per-stage scope accounting](evidence/r1-restore-waterfall.csv)

## Late join

Raising the cap cut median verified join time by about 73% at 50% occupancy and 74% at 90%. The accounting changed order as well as rate. At 90% with cap 3, the piece identities were largely processed before the two assembled boards finished. With cap 12, both board baselines finished early and identities continued across the remaining interval. In the four NetTrace-only controls we independently counted one piece creation and one complete typed identity for every unique object driver plus exactly two complete typed board values. At 90% these enclosing logical serializer scopes totalled 878,416 identity bits and 2,072,946 board bits. These totals exclude surrounding traffic and protocol overhead.

Across the four cap-12 repeats per density, the board fields finished within 181 / 347 ms of observed open, while the final identity field finished at 1,084–1,107 / 1,928–1,958 ms including boundary uncertainty. Only 12–31 / 23–43 ms remained between the final typed packet and verification. The final successful public manifest check itself took about 18–21 ms at 50% and 35 ms at 90% in four representative captures. These intervals overlap and cannot be summed. The client spends most of the cap-12 miss waiting for, and processing, the sequence of required updates. Reducing only the work after the final required typed read cannot close the gap. The two-board restore cost and the join identity tail implicate different paths. A smaller board encoding alone has no demonstrated path to recovering the entire join residual. [Repeated client profiles and frame tails](evidence/r1-join.md) · [Independent control packet audit](evidence/r1-control-typed.csv) · Packet decoder (source workstation, `r1_nettrace.py`)

**Client frame cost.** In the four repeats per setting, frames over 16.67 ms rose from 2–4 to 30–31 at 50%, and from 4–5 to 49–50 at 90%. Per-run p95 rose from 1.7–7.3 to 21.6–22.4 ms and from 4.3–7.7 to 24.4–25.6 ms, respectively. The single worst frames decreased in these repetitions. Frequency and distribution of stalls explain the tradeoff better than the earlier single-pair maximum. [Per-run tails and clocks](evidence/r1-join-runs.csv) · [Final verifier bounds](evidence/r1-join-final-verify.csv)

## Adversarial checks and scope

* **Concurrent work.** During the fourth block a separate Toolbox build began at 18:25:22 UTC. UBT started at 18:25:28. A host check during the failed retry found the C++ compiler and linker consuming multiple cores. Two relay-rejected runs matched the manifests but exceeded the 5 ms forwarding tolerance. Two other runs overlapped the external build while satisfying the relay validator. All four are retained as sensitivity observations. The primary comparison uses replacements at the original density and cap. Subsequent runs use a process guard for compiler activity. The first blocks lack a continuous machine-wide utilization record. [Compiler sampling during the guarded runs](evidence/r1-compiler-guard.csv)
* **Layer accounting.** GameThread wall-time scopes include time spent in unnamed descendants and any off-CPU time inside the scope. Named child times are excluded from parent self time. Packet-content fields can be nested or reconstructed from multiple datagrams. Neither a field bit count nor a snapshot file size directly measures its share of physical-link traffic.
* **What constitutes usable.** Board and identity packet timestamps mark end-of-packet processing on the client. A received board may still await identities, composition or publication. The receipt timestamp includes output and supervisor polling. Only the fixture's verified open-to-manifest stopwatch determines the join budget. A guard-based inference about verification attempts is recorded separately from a direct call count.
* **Diagnostic limits.** The four native offline authority exports wrote timing data and exited with memory-tag errors. Independent GameThread scope and frame reconciliation supports their timing use. Release memory ownership, packaged startup errors, offline save-inspector rejection and whole-flow endpoint delivery remain independent open gates. The runs exercised a single joining client. They cannot establish fairness to an established client. The caps apply only to these processes.

## Reproducing the evidence

Run the cohort auditor from the checkout after the live runs complete. It verifies executable paths and hashes, the per-role launch flags, server cap readbacks, manifest hashes and row counts, relay admission, repeat counts, run order and non-overlap. The dashboard uses only the admitted runs. Keep the exclusion ledger when comparing future measurements. Cohort audit (source workstation, `r1_cohort.py`) · [All admitted pairs](evidence/r1-cohort.csv) · [Excluded attempts](evidence/r1-exclusions.json) · [Staged executable fingerprints](evidence/r1-executables.json)

The restore and join reports link their raw timers, packet fields, frame distributions and independent reconciliation. To replay the ordered GameThread log markers from a trace, run Python with UTF-8 output, e.g. `python -X utf8 docs/campaigns/hex-grid/evidence/r1_clock.py <role.utrace>`. Clock extraction (source workstation, `r1_clock.py`) · [Server marker samples](evidence/r1-clock-server.csv) · [Client marker samples](evidence/r1-clock-client.csv)

## Narrow diagnostic scope proposal

| Unresolved choice | Measurements that would distinguish it | Verification |
|---|---|---|
| EntityScript spawn and initialization | Subdivide the existing spawn request around object acquisition, bridge linking, parameter injection, construction and completion. Count each outcome and policy. Separate BeginPlay from the ECS request it enqueues. | Reconcile self and child times within the same restore frame. Keep mixed composition, pre-BeginPlay saved properties, stable identity and object count identical. |
| Board decode versus per-object hydration | In DoHydrate_Enqueue record slot/table validation, deserialize and enqueue totals by payload type. In FProcessor_Hydration_Dispatch record attempts and successful, pending and rejected applies for each type. Split board projection replacement and object identity reconciliation. | Reconcile counts to exactly two boards and every object identity. Preserve atomic quarantine, sibling visibility and consecutive convergence frames. Include released setup work from the subsequent frame. |
| First materialized client state versus fixture scanning | Mark first/last accepted board revision, unique identity installations, final required binding, and first public usable query. Add a matched Verify entry/exit counter with early-return reason. Record both clock endpoints on the same monotonic clock, alongside the existing receipt. | Match typed packet counts to unique driver IDs, public manifest and teardown. Ensure probe overhead is measured with capture off and all benchmark clocks remain intact. |

These scope additions are proposals for a separate diagnostics pass. No runtime behavior, serialization, game setting or public interface was changed for R1.
