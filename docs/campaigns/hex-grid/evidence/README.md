# Hex-grid design and qualification digest

The typed hex board lives in CkGrid alongside the square grid. Geometry and authoring are separate from board occupancy and object lifetime. The authority owns saved placement and publishes the baseline that replicated clients use. The editor painting feature writes authored data for subsequent loads.

| Deliverable | Contract or evidence |
| --- | --- |
| Coordinates, orientation, geometry and board composition | [Geometry](../PHASE_1.md), [board authoring](../PHASE_2.md), [board gym](phase-2-captures.jpg) |
| Footprints, blockers, placement and teardown | [Footprint contract](../PHASE_3.md), [placement contract](../PHASE_4.md), [blocker gym](phase-3-captures.jpg), [placement gym](phase-4-captures.jpg) |
| Authority persistence and replicated readiness | [Restore design](../PHASE_5.md), [late-join design](../PHASE_6.md), [restored board](phase-5-restored.png), [client board](phase-6-client.png) |
| Saved editor paint | [Authoring contract](../PHASE_7.md), [reopened pointy board](phase-7-paint-reopened.png) |
| Release workload, budgets and open gates | [Execution record](../PROGRESS.md), [remediation plan](../PHASE_8_REMEDIATION.md), [verification procedure](../VALIDATION.md) |
| Performance attribution | [Restore analysis](r1-restore.md), [join analysis](r1-join.md), [R2A authority timing by density](r2a-restore-summary.csv) |
| Pooled ActorRelay save inspection | [Packaged inspection results](actorrelay-key-packaged.csv) |
| Pre-hex compatibility fixtures | [Square](../../../../Plugins/CkTests/TestData/CkGrid/PreHexSquare.sav), [inventory](../../../../Plugins/CkTests/TestData/CkGrid/PreHexInventory.sav) |

The gate record describes the runs on the original workstation. Raw logs, archives, process traces, package stages and replay helpers named in the historical record are workstation artifacts. CSV path columns identify original observations. JSON receipts use ${SOURCE_CHECKOUT} for that workstation’s checkout root. Case identifiers, binary and slot hashes, and measurements retain their original values. Use the committed tables for the recorded observations and the verification procedure for fresh runs.
