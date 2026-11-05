# UE 5.8 delivery verification

On 2026-11-04 the maintainer instructed this delivery to stop further walker repairs,
skip automated walker tests, verify the remaining framework, and publish the six
authorized repositories.

## Walker exclusions

[UE58-Walker-Exclusions.json](UE58-Walker-Exclusions.json) records the exact 368 omitted
test names and their source identities. The omissions cover procedural walker gait,
surface motion, body pose, feet, footholds, support, recovery, height planning,
contact staging, walker-specific action integration, original walker routes, and
walker visualization tests. A mixed test that requires a walker is omitted as one
registration; its independent nonwalking siblings remain included.

Standalone action builders, claims and articulation, rig/IK, leg-curve and chain
clearance tests, body-only action tests, general body-enclosure arithmetic, and
debugger-history tests remain in scope. Crowd, navigation, generic locomotion,
ControlRig, RuntimeMesh and ProceduralMesh are not excluded by this decision.

The verification invocation temporarily adds exact-name `deferred` entries to the
host AutomationGate.json. Its existing roots and all 55 known-red entries across
the host and plugins are preserved. The original host file is restored byte for
byte after the run is archived. No test assertion, deadline, admission limit,
query budget or permanent default gate is changed by these omissions.

## Unverified walker behavior

Existing approved walker implementations are included in the delivery. This scoped
verification does not certify original Posts or Pillars traversal or the complete
native four-placement stance-preparation lifecycle. Their last original-route runs
remain failures. The experimental native formation fixture was removed after an
ordinary RR takeoff falsified its initial retained-plant premise.

Feet-normal compatibility was approved but is deferred under the later instruction
to stop further walker repairs. It is not implemented in this delivery. Earlier
focused/Core results do not substitute for the omitted native route verification.

## Remaining-framework gate

The gate runs the configured project population with only the documented temporary
walker deferrals, using fresh discovery, a fresh serial editor, D3D12 and RHI
validation. It does not use a positive test-name filter or skip renderer tests.
The existing tiny GitLink linked-worktree test fixture remains limited to
`Saved/GitLinkTests/<fresh-guid>/worktree`, as separately authorized.

The final gate completed on 2026-11-05 UTC with exit code 0:

- Fresh discovery: 7,574 tests; configured project population: 4,537.
- Exact walker omissions: 368; selected and completed unique tests: 4,169.
- Initial results: 4,156 successes and 13 listed failures. Two listed flaky cases
  passed their automatic retries, leaving 4,158 successes and 11 known reds.
- No new failures, missing results, unrequested tests, skipped results or
  contamination. The 50 required repair/sibling checks and the corrected Texture
  authored-window case all succeeded.
- Five editor boots: two discovery boots, two main/network runtime boots, and one
  grouped flaky-retry runtime boot. There were 4,171 completion events including
  those two documented retries.

The native source/output checks matched 9,606 source entries, 26 walker guards and
157 compiled products. All original gate configurations were restored, including
the host SHA256 `D27D3558D150BBC3605D90C3541C5FF62566E77F1323CF82D5A485ACA2E1DD14`.
All 55 known-red entries remain unchanged. Eleven known reds remain; this is a
passing scoped gate under that existing policy, not an assertion that every test
or omitted walker route passes.

Native log review attributed the expected negative-control errors to their source
tests and found no additional primary, fatal, script-compilation, math or RHI
errors. Existing pre-cleanup fixture entity-count diagnostics remain recorded;
variable counts alone do not prove persistent leaks or successful cleanup. No
repository-wide leak-free claim is made.

The remaining Texture debugger failure was a stale test lookup: authored tab
headers are an actual `SButton` subclass. The corrected lookup accepts that exact
subclass while retaining every physical-click, page-selection, reload, screenshot
and teardown assertion. Its focused real-renderer cohort passed 31/31 before the
complete final gate passed. An earlier PoseWorkspace click failure did not
reproduce; its original uninstrumented test passed the final gate. No speculative
UI repair or permanent diagnostic observer is included.

## Delivery boundary

The delivery targets are the host, Foundation, Tests, Debugger and GitLink `dev`
branches and the selected engine fork's `main-ck` branch. Plugin gitlinks advance
only to remotely verified published commits. The final delivery receipts record
the exact six published identities separately from this verification record.

Only the two portable verification files in this directory are allowlisted;
other local workspace documentation remains ignored. Test-owned Sproutling
resaves were backed up and restored through the repository's normal Git filters.
Unrelated engine Flutter deletions and `Unreal.natvis`, local vendor plugin
directories, solution files and the continuation prompt were preserved.
