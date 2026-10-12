# Art Viewer time track - approved implementation

User reports the scrubber does not wrap in Loop or return in PingPong, and requests a clearer timeline inspired by video and pixel-art tools. Sproutling must appear in the preview and timeline. The user approved the Time track on 2026-10-12 with duration-proportional blocks, independent Fit/2x/4x/8x timeline zoom, horizontal scrolling, and fixed-size thumbnails that clip instead of shrinking.

## Verified diagnosis

`CkPixelArtViewer_Layout.cpp::Build_Timeline` clamps the absolute `_TimeMilliseconds / _PreparedCycleMilliseconds` to [0,1]. The absolute clock deliberately remains unbounded in Loop/PingPong, while the prepared animation evaluator wraps frame selection. This locks the slider at the end and hides the return leg. The adjacent time readout also uses absolute time. Thumbnail widths are clamped to 70–100 px, so they do not faithfully show relative frame holds.

## Proposals

- **Time track (recommended):** one time ruler and playhead over duration-proportional frame blocks, each showing a Sproutling thumbnail, frame number and hold. Preview and inspector show the selected source. Returning direction is explicit; Loop wraps to the start.
- **Frame cells:** equal-size pose cells with frame-number ruler and explicit hold labels. Easier pose comparison; unequal duration is conveyed by labels rather than width.

Interactive mockup: thread visualization `pixel-viewer-timeline.html`. It embeds all eight corrected source grids and actual holds (450/220/220/90/110/220/220/450 ms, 1980 ms authored total). Both proposals share playback controls and use the same data. Playback starts only on user action.

## Timing contract for the implementation

Keep the absolute clock and prepared animation authoritative. Derive positive cycle phase for display; Once clamps. Map PingPong return visits backward through each authored frame interval, with endpoint frames visited once as in the current core sequence. Do not silently duplicate endpoint holds or change animation duration to make the thumb bounce. Scrubbing should preserve the current return leg when that frame has both visits. Manual frame selection needs a displayed position consistent with the pinned frame. Cover reverse/negative time, exact cycle boundaries, varying holds, Once completion, manual override, sampling and source retention before shipping native changes.

## Prototype evidence before approval

Source-grounded read-only diagnosis completed. Mockup syntax and deterministic behavior checks pass: eight source frames, loop wrap, negative time, ping-pong return, return-leg seek, Once clamp and manual selection. Both proposals were inspected in the browser; real frame stepping synchronizes preview, source, duration, highlight and playhead. Play/Pause and proposal switching work. Ping-pong was observed on its returning leg (authored position 0.829 s decreasing to 0.746 s with Returning indicator); Loop position wraps while the clock advances. The prototype ignores its own persisted-state echo so it cannot reset active playback. Native viewer source has not changed in this proposal stage. No Unreal builds, Git commits or publication performed.

Inspiration: Blackmagic's official Resolve Edit page and Aseprite's timeline/frame-duration documentation. The viewer remains an inspection tool; no source editing, trimming or reordering is proposed.

## Native implementation

The time track uses fixed 56 px thumbnails clipped to each authored duration block. A separate timeline zoom menu expands the track inside a horizontal scroll viewport; canvas zoom stays independent. One painted playhead and seconds ruler replace the old slider and clamped-width thumbnail buttons. Positive phase mapping wraps Loop and folds the PingPong interior return visits onto the authored forward axis. Sampling applies to the displayed timing; frame retention affects preview selection without retiming the track. Manual stepping uses the selected frame prefix. Endpoint visits remain unchanged in the runtime evaluator.

Focused native state and mounted Sproutling coverage added; native acceptance complete. Approval reference: `C:/Users/sulfu/.codex/visualizations/2026/10/12/01a13027-3e81-7b03-a035-7efa48820990/pixel-viewer-timeline-zoom.html`.

## Acceptance - 2026-10-12

`Saved/Logs/PixelSprite-TimelineGate6.log`: incremental editor build succeeded; `Ck.PixelArtViewer` focused gate 5/5 passed, 0 failed/skipped/contaminated, 53 seconds test duration. Four mounted tests ran with the real renderer. State coverage includes negative/exact Loop wrap, PingPong return and inverse seeking, Once endpoints, reverse, manual pins, sampling, retention, and rejected malformed input. Mounted Sproutling checks actual imported durations, a 5:1 block ratio, fixed 56 px thumbnail clipping, 8x full reveal, physical zoom menu and pointer scrubbing, horizontal scroll, and Studio/Focused state preservation. Malformed candidate rejection preserves the existing track; both emitted CK diagnostics are explicitly expected.

Final Fit and 8x native screenshots were inspected: `Saved/PixelSpriteAcceptance/Sproutling-TimeTrack-Fit.png` and `Sproutling-TimeTrack-Zoom.png`. Text encoding is explicit UTF-8; native glyphs are readable. Earlier build attempts stopped before boot on missing explicit ensure/format includes and an indexed Slate child-list API fix; rendered iterations exposed non-finite zoom acceptance and the dual diagnostic expectation, both fixed and re-gated. The final fresh renderer log contains only the intentionally tested timeline rejection, with no unexpected test errors or script reload contamination.

The accepted implementation is included in the direct dev publication batch; unrelated staged/dirty work preserved. This is a focused editor viewer acceptance, not a full-suite or packaged-runtime claim.

## Direct dev publication - 2026-10-12

The approved creature, viewer layouts/time track and world gym are included in the direct dev publication batch. Submodule tips verified on origin/dev: Foundation `562da71fd1c4`, GameplayDebugger `e05ddc4e85cc`, Tests `4f4f4bc355b7`. Incremental build and focused Ck.Pixel acceptance passed 58/58 with five rendered tests, 0 skipped/contaminated; rendered PixelSpriteGym passed in 24s with its documented map/game override. No rebase was needed because all three fetched submodule bases matched the opening tips. Unrelated instructions, build profiles, procedural animation work and staged tags are excluded.
