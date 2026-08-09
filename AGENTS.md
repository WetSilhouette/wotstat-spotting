# AGENTS.md

Guidance for coding agents (and humans) working in this repository.

## Project Overview

WotStat Spotting Visualizer is a World of Tanks mod that visualizes the
player's **own vehicle's** spotting geometry — its 6 visibility
checkpoints and 2 view range ports — plus derived stats (effective view
range, camouflage %, angle-based exposure hints). It is intended for
Garage, Replays, and Training Rooms only. The runtime restriction logic
must remain in place for all competitive battle modes (Random, Ranked,
Clan, Team/Company).

The mod is packaged as `wotstat.spotting_<version>.wotmod` and copied as
`wotstat.spotting_<version>.mtmod`.

Full design rationale lives in `CONCEPT.md`; the granular build checklist
lives in `TASKS.md`. Read both before making non-trivial changes — this
file covers constraints and conventions, not the "why."

## Repository Layout

- `res/scripts/client/gui/mods/mod_wotstatSpotting.py` is the WoT mod
  entry point.
- `res/scripts/client/gui/mods/wotstatSpotting/WotstatSpotting.py`
  contains the main runtime controller.
- `res/scripts/client/gui/mods/wotstatSpotting/core/` contains
  geometry constants, per-frame transform resolution, derived-stat
  calculators, exposure heuristics, and overlay rendering.
- `res/scripts/client/gui/mods/wotstatSpotting/utils/` contains the
  restriction gate, compatibility helpers, i18n, and logging.
- `res/mods/wotstat-spotting/*.dds` are runtime textures for overlay
  markers.
- `meta.xml` is the packaged mod metadata template.
- `build.sh` builds the release/debug mod archives.
- `NOTES.md` captures Phase 1 research findings (confirmed API calls,
  data locations) — treat it as living documentation, keep it updated
  whenever a new game API dependency is discovered or a version bump
  changes something.
- `CONCEPT.md` / `TASKS.md` are planning documents, not runtime code —
  don't ship them inside the `.wotmod`.

## Runtime Environment

- The in-game code targets the World of Tanks Python 2 runtime.
- Keep syntax Python 2 compatible: no f-strings, no variable
  annotations, no keyword-only arguments, and no Python 3-only
  standard-library APIs.
- WoT/BigWorld modules (e.g. `BigWorld`, `Math`, `ResMgr`,
  `BattleReplay`, `PlayerEvents`, `gui.*`, and whatever vehicle/entity
  modules Phase 1 research confirms) exist only inside the game client.
  Do not assume a call exists without a confirmed entry in `NOTES.md`;
  mark unverified calls `# TODO(api-verify)` in code.
- Do not replace game API calls with local stand-ins in production
  code. If local checks are needed for pure-logic testing (e.g. stat
  formula math), keep that logic in files with no game-API imports so
  it's testable in isolation, and keep the game-API glue code separate.

## Coding Conventions

- Preserve two-space indentation, matching the wider wotstat mod family
  style.
- Prefer package-relative imports inside `wotstatSpotting`.
- Use `utils.logger.log()` for mod logging — no bare `print`.
- Keep source text ASCII unless a file already contains or needs
  localized text, such as `utils/i18n.py`.
- Preserve placeholder values used by `build.sh`:
  - `{{VERSION}}` is replaced by `build.sh`.
  - `'{{DEBUG_MODE}}'` is replaced by `build.sh`.
- Keep per-frame work cheap and incremental. Checkpoint/port transforms
  update every tick while the overlay is active — avoid allocating new
  marker objects each frame; reposition existing ones instead. Follow
  wotstat-vegetation's `awaitNextFrame()`-style yielding pattern for any
  future bulk operation that iterates many objects at once.
- Avoid broad refactors around BigWorld callbacks, event registration,
  transform-resolution logic, or the restriction gate unless the task
  specifically requires it — these are the highest-risk areas in the
  codebase for silent behavioral regressions.

## Behavior Constraints — read this section twice

- **Never render, compute, or expose any data about a vehicle other
  than the player's own.** No spotted-enemy visualization, no
  unspotted-enemy prediction, no exceptions for "debug only" builds.
  This is a permanent scope wall, not a v1 limitation to relax later.
- The mod must remain fully inert outside Garage, Replays, and Training
  Rooms. Respect `utils/restriction.py` and the user-facing README.
- `isAllowedContext()` in `utils/restriction.py` must fail closed: if
  the current mode can't be reliably determined, treat it as
  disallowed, never as allowed.
- Every rendering entry point and every per-frame update hook must
  check `isAllowedContext()` before doing any work — not just before
  rendering, but before any computation, however cheap.
- If the game mode changes mid-session (e.g. leaving a Training Room),
  any active overlay must be force-cleared if the new context is
  disallowed. Don't rely on the toggle state alone to gate visibility.
- Keep optional `wotstat-debug-utils` integration optional. Imports
  from `gui.debugUtils` must continue to fail gracefully.
- Derived stats (effective view range, camouflage %) must be computed
  only from data the client already has locally (own vehicle stats,
  equipment, crew, consumables, terrain under own vehicle). Never
  extend these calculators to accept or reference any other vehicle's
  data.

## Required Manual Tests Before Any Release

These are not optional and are not covered by any automated suite —
run them by hand every release, especially after touching the
restriction gate or the per-frame update path:

1. **Inert-in-competitive-modes test**: queue into a Random Battle,
   attempt to toggle the overlay. Confirm nothing renders, no errors
   are logged, no partial state is created.
2. **Forced-cleanup-on-transition test**: enable the overlay in a
   Training Room, then transition to a disallowed context. Confirm the
   overlay is force-cleared, not just hidden-but-still-updating.
3. **Own-vehicle-only test**: with other vehicles present (Training
   Room with bots/other players, or a Replay with visible enemies),
   confirm no markers, labels, or stats ever appear for anything but
   the player's own vehicle.

## Caches and Generated Data

- If any research-derived per-vehicle data ends up cached (see
  `core/runtimeCache.py`, if/when created), tag the cache format with a
  version constant from the start.
- Do not commit generated `build/`, `.pyc`, `.wotmod`, `.mtmod`, or
  local runtime cache artifacts.

## Build Commands

Use the provided script:

```
./build.sh -v 1.0.0
```

For a debug build:

```
./build.sh -v 1.0.0 -d
```

The build script:

- removes and recreates `build/`
- copies `res/`
- substitutes version/debug placeholders
- runs `python2 -m compileall ./build`
- packages compiled `.pyc` files, `meta.xml`, and `.dds` textures
- writes `.wotmod` and `.mtmod` archives at the repository root

## Verification

There is no automated test suite for game-API-dependent code in this
repository (the API only exists inside the live client). For code
changes:

- Run `./build.sh -v <version>` when Python 2 is available; treat
  successful packaging as a basic smoke test.
- Pure-logic code (stat formulas, geometry math with no game-API
  imports) can and should be verified independently of the game client
  where feasible.
- For anything touching game APIs, the restriction gate, or per-frame
  transforms, run the three Required Manual Tests above in the game
  client, a Replay, or a Training Room.
- If Python 2 or the game client is unavailable, say so clearly in the
  final response and explain what was checked instead (e.g. syntax
  review only, no runtime verification).

## Documentation

- Keep `README.md` and `README_EN.md` aligned when changing public
  behavior, install steps, hotkeys, supported modes, or screenshots.
- Use English for `README_EN.md` and Russian for `README.md`.
- Keep `NOTES.md` updated whenever a new game API dependency is
  discovered, confirmed, or found to have changed after a game patch.
- Update this file when project workflows, constraints, or the
  Required Manual Tests change.