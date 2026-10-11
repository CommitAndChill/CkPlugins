# Native manifest implementation contract

Maintainer decisions: malformed artwork is a structured ordinary failure in every build. Native source loading accepts only ordinary files/directories, rejecting every symlink/junction traversal component even when its target is inside the root. This differs from the Python loader. The loader assumes a stable local authoring tree; this does not claim race-free confinement against concurrent hostile filesystem mutation.

## Value ownership and publication

Parse schema into a temporary manifest before touching source files. Frames store source strings and stable integer indices into one owned source table. Each exact normalized source spelling is decoded once; frames never duplicate its palette/grid. No array-element addresses survive source-table growth. Publish the caller output only after every required source, dimension and frame validates. Late failures must preserve a sentinel output exactly.

The public value model contains canvas dimensions, ordered animations, authoritative frame `_DurationMilliseconds` doubles, playback, anchors, source indices and validated JSON fragments for metadata/events. `Get_Duration()` converts one authored frame duration to FCk_Time seconds for consumers; that convenience value is not the source for authored boundary arithmetic. Json is private; no public DOM ownership. Fragments preserve nested types and raw numeric lexemes; they are not called canonical JSON. Defaults are [] for events and {} for metadata.

## Recognition before DOM allocation

Bound text/bytes at 8 MiB. A token pass rejects duplicate decoded object keys, malformed syntax, nonfinite floating numbers, depth above 64 and nodes above 100000, counting object keys. Validate exact integer lexemes for version, canvas dimensions and anchor coordinates; bool, quoted numbers, 1.0 and 1e0 reject at those fields. Preserve arbitrary integer metadata lexemes without conversion to double. Reject unknown schema fields and explicitly diagnose unsupported layers.

Version is exactly integer 1. Canvas dimensions are 1..4096 and product at most 1048576. Animations are 1..1024, names 1..128 characters. Playback is loop, once or ping-pong. Each animation has a nonempty frame array; total frames at most 4096 and sum of canvas pixels per frame at most 16777216. Duration is a finite number strictly above zero and at most 86400000 milliseconds, and its seconds value must remain positive in native double precision. Native loading explicitly rejects tiny positive Python-compatible durations that underflow to zero seconds; this is a subset limitation, not full Python/native parity. Anchors are at most 256 per frame, names 1..128, exactly two integer coordinates inside canvas. Events are arrays and metadata objects at all three levels.

`TryEvaluate_AnimationMilliseconds` converts each authored duration and input time from double to its shortest round-trip decimal representation, then sums, compares boundaries and computes modulo in that decimal domain. For example, authored 0.1 and 0.2 millisecond frames transition at 0.3, including half-open nextafter neighbors. The `TryEvaluate_Animation` FCk_Time overload starts with the shortest round-trip decimal seconds value and shifts its exponent by three to milliseconds, so even very large finite seconds need no overflowing double multiplication. Frame selection follows those exact decimal comparisons; only the presentation local time may be clamped to the next representable double below the frame duration after selection. The generic `TryEvaluate_Frame` remains the separate seconds-based evaluator and is unchanged by this authored timing contract. Invalid time, duration, playback or sequence length leaves the selection output untouched.

## File admission

Sources are at most 1024 characters, forward-slash relative .xpm paths. Reject absolute/drive/UNC, backslashes/colon, empty/dot/dotdot segments, control characters including C1, Windows metacharacters, trailing dots/spaces and reserved devices. Require existing ordinary root components, child directories and final file; an attribute failure cannot be accepted merely because IsSymlink returns NonSymlink. Reject unsupported link inspection.

Use the physical platform file value-result OpenRead overload and its owned handle. Bound Size before allocation and Read; detect short/changed reads. Validate UTF-8 strictly before constructing FString. Each XPM is at most 8 MiB; aggregate unique source spellings total at most 64 MiB. Every decoded grid must match canvas. Caching keys are validated normalized ordinary paths with explicitly case-sensitive equality.

## Focused acceptance

Valid checked-in Character.json, repeated A/B/A sources, stable indices after table growth, one source for 4096 repeated frames, and nested extras including huge integer metadata must pass. Test duplicate escaped keys, depth/nodes, exact integer fields, malformed/trailing JSON and UTF-8, all dimensions/count/duration/anchor boundaries, path/device/link cases, missing/oversize/dimension-mismatched sources, aggregate budgets and late-failure sentinel preservation. The prior focused native gate built and passed 13 of 14 tests but failed the manifest timing boundary; NativeManifestGate4 built and passed all 15 focused tests with exit 0. Python success does not prove native parity.

Native source caching uses exact normalized source spelling. Repeated identical references share one decoded source. Different case spellings remain distinct, including on Windows, so case-sensitive directories cannot alias different artwork; aliases count separately toward the aggregate byte limit.
