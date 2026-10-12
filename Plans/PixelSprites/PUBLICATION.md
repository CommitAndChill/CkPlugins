# PixelSprite direct dev publication - 2026-10-12

Publishes the approved Sproutling animation and corrected shoulder pixels, shared Studio/Focused viewer layouts, zoomable duration-proportional time track and Loop/PingPong playhead fixes, and the three-station world gym.

## Submodule commits

- `Plugins/CkFoundation` `d6536efca934` - feat(pixel-sprite): add the Sproutling idle example
- `Plugins/CkFoundation` `562da71fd1c4` - feat(pixel-sprite): present committed animation frames in world materials
- `Plugins/CkGameplayDebugger` `d3c4f3364f77` - fix(pixel-art-viewer): map playback onto authored timeline time
- `Plugins/CkGameplayDebugger` `e05ddc4e85cc` - feat(pixel-art-viewer): add shared layouts and a zoomable time track
- `Plugins/CkTests` `4f4f4bc355b7` - feat(pixel-sprite): add the shader and box-pixel world gym

## Integration and gates

All three submodule origin/dev bases matched the opening tips. No rebases, conflicts, rewritten tips or backup branches were necessary. Their five new commits were fast-forwarded and the resulting tips verified on origin/dev. CkPlugins origin did not advertise a dev branch; the explicit direct-dev instruction creates it from the tested PixelSprite delivery branch. Existing historical root commits are retained.

`UnrealToolbox --build --generate --target=Editor --test --test-pattern=Ck.Pixel --parallel=1 --known-reds=off --no-live --project=D:\Repos\CkPlugins --output=Saved/Logs/PixelSprite-PublicationGate1.log` exited 0. The gate passed 58/58, failed/skipped/contaminated 0; five tests ran with the real renderer, duration 1m33s.

`UnrealToolbox --gauntlet=PixelSpriteGym --gauntlet-visual --gauntlet-map=/CkTests/TestGyms/TestGyms_CkTests_Level?game=/Script/Angelscript.Ck_PixelSpriteGym_GameMode --project=D:\Repos\CkPlugins --output=Saved/Logs/PixelSprite-PublicationGym2.log` exited 0, 1/1 passed in 24s. The earlier PublicationGym1 invocation omitted the map and renderer options and timed out waiting for the controller; the corrected documented invocation passed without implementation changes.

The temporary credential used for publication was explicitly authorized; no credentials were added to remote URLs or tracked files. Outgoing ranges passed credential/private-key scans, and a separate bounded review verified the exact five submodule file manifests.

## Commit boundaries and preserved work

The current-pixel query, passive material presenter and runtime tests stay together. Gym scripts, ownership-checked authoring fixture, shader/cube materials and quad stay together. The host Gauntlet registration stays with verified submodule pointers. The imported creature and sidecar are a separate host sample commit; acceptance documentation is separate.

Unrelated root instruction migrations, build-profile hooks, engine association, generated script work, staged/unstaged gameplay tags, CkApplication/GitLink pointers, scratch assets and drafts remain local. Foundation instruction migrations/build settings and ensure-policy edits remain local. CkTests procedural-animation work and the debugger grid-editor continuation remain local. The exact excluded path/hash inventory is preserved at `Saved/PixelSpriteAcceptance/PublicationExcluded.json`; it is local diagnostic evidence, not a shipping artifact.

This is focused feature acceptance, not a new full-suite or packaged-runtime claim. The previously deferred outside failures remain deferred.
