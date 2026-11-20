# Authority restore on the qualification workstation

**Entity rebuild is the largest observed interval.** From SaveKey resolver readiness through complete entity mapping, the packaged server spent 539–548 ms at 50% occupancy and 1,079–1,140 ms at 90%. This accounts for 46–50% and 54–58% respectively of each run's request-to-verified-manifest time. Even if this whole interval vanished with every other interval held constant, the five runs would still take 548–646 ms and 804–921 ms. Reaching 250 ms requires gains across multiple stages.

## Measurements

Win64 Development packaged dedicated server, i9-10900KF and 96 GiB RAM, two radius-32 boards, 3,168 or 5,704 total placed objects. The same qualification workload performed normal save, teardown, OpenLevel travel without clients, world reconstitution and full public manifest verification. One fresh process per sample, five measured per density, first warmup per density excluded. Cells below give **median / nearest-rank p95 (sample maximum)** in milliseconds. Use individual rows when calculating a sum or share. [Per-run intervals](restore-intervals.csv)

| Wall interval | 50% | 90% |
|---|---:|---:|
| Table provenance logged → load-start logged | 7 / 8 | 13 / 14 |
| Load-start logged → teardown drained | 16 / 18 | 32 / 33 |
| Teardown drained → engine browse starts | 17 / 18 | 2 / 3 |
| Browse starts → map load completes | 121 / 122 | 170 / 175 |
| Map complete → resolver rehydrated | 2 / 2 | 2 / 2 |
| Resolver rehydrated → rebuild complete | **544 / 548** | **1,091 / 1,140** |
| Rebuild complete → quarantine stamped | 37 / 57 | 37 / 38 |
| Quarantine stamped → payloads enqueued | 73 / 103 | 129 / 130 |
| Payloads enqueued → quarantine lifted | 75 / 77 | 139 / 140 |
| Quarantine lifted → drain declared complete | 72 / 73 | 122 / 123 |
| Drain declared complete → ready to resume | 74 / 76 | 78 / 79 |
| Both unmarked edges combined | 97.8 / 107.5 | 149.6 / 195.0 |
| **Request to verified manifest** | **1,144.5 / 1,193.8** | **1,962.2 / 2,002.6** |

Mean request-to-verification was 1,135.5 / 1,962.5 ms (50% / 90%). Mean rebuild was 544.0 / 1,097.2 ms. Marker precision is one millisecond. Rebuild includes two frame transitions and the work between them. Every measured run mapped all 3,174 / 5,710 entities in two rebuild frames and enqueued every payload. No convergence condition was outstanding at ready. Independent checking reproduced the cohort timing and SHA-1 of each exact manifest from the archived role outputs. Each server subsequently failed offline save inspection. Those failures and startup diagnostics remain separate release blockers. Source archive (source workstation, `phase-8-workstation.zip`)

## Attribution and next experiment

* **Rebuild.** The slot provenance logged 3,170 / 5,706 actor-bridged runtime rows, alongside two engine-owned and two construction-spawned rows per run. The reconstruction loop can resolve or spawn, finish construction, obtain a bridge entity and pump the LoadKernel scheduler. Two rebuild frames at both densities and zero skipped rows rule out a many-frame stall as the explanation here. The interval also includes work elsewhere on those frames. The logs cannot assign exclusive CPU times or establish that every runtime row called SpawnActor. Capture GameThread CPU/frame scopes during these two frames and separate actor creation, component registration, entity/bridge construction, table traversal, kernel pump and frame pacing before selecting a fix. [Rebuild implementation and kernel pump](../../../../../Plugins/CkFoundation/Source/CkSnapshot/Public/CkSnapshot/Subsystem/CkSnapshot_Subsystem.cpp#L1018)
* **Hydration.** After quarantine stamping the loader deserializes and submits saved payloads. Two board values account for 4,548,484 / 8,187,644 payload bytes, and 3,168 / 5,704 identity values account for 522,720 / 941,160 bytes. Record counts and bytes make both payload families worth measuring separately. Byte share alone cannot attribute CPU. The subsequent enqueue-to-lift interval includes reconciliation and the full scheduler pump. Lift-to-drained also includes the time allowed for released setup to run. Profile board decode, per-object decode, apply, projection/index publication, subsequent setup and idle time separately. [Enqueue and decode](../../../../../Plugins/CkFoundation/Source/CkSnapshot/Public/CkSnapshot/Subsystem/CkSnapshot_Subsystem.cpp#L1771) · [Quarantine release and drain rules](../../../../../Plugins/CkFoundation/Source/CkSnapshot/Public/CkSnapshot/Subsystem/CkSnapshot_Subsystem.cpp#L3530)
* **Travel and readiness.** The map load takes 117–122 / 169–175 ms between engine markers. The final drain-to-ready bracket includes two convergence frames on a 30 Hz dedicated server. Current traces for this qualification cohort have no CPU timeline. The marker timestamps cannot separate wall-clock pacing from active world teardown, GC, map initialization or final convergence work. The unmarked residual combines request entry through provenance logging with ready through harness verification. It includes slot reading/validation and complete manifest enumeration on opposite ends of the operation. Add separate diagnostic boundaries if default engine CPU scopes cannot resolve it. Retain the published request-to-verified-manifest metric. [Request entry](../../../../../Plugins/CkFoundation/Source/CkSnapshot/Public/CkSnapshot/Subsystem/CkSnapshot_Subsystem.cpp#L570) · [Acceptance timer boundaries](../../../../../Plugins/CkTests/Source/CkTests/Private/HexGrid/CkHexDenseAcceptance.cpp#L427)

Reproduce the CSV with Python 3 from this directory using `python restore_profile.py`. The reader takes its inputs from the adjacent qualification archive, checks the raw manifest bytes, recorded timings, rebuild and payload accounting, then emits the rows in cohort order. Archive reader (source workstation, `restore_profile.py`)
