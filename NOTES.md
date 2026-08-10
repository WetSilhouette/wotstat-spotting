# NOTES.md — Phase 1 Research Findings

Living document. Update whenever a new game API dependency is
discovered, confirmed, or found to have changed after a game patch.
Every entry below is sourced — treat unsourced claims elsewhere in the
codebase as unverified until they get an entry here.

---

## Status: Phase 1 core question — ANSWERED

**Is checkpoint/port data stored, or only derivable from the model
rig?** Confirmed: **stored**, as static fields on the vehicle's type
descriptor, computed once from hull/turret geometry — not something
that needs per-frame recomputation from scratch.

---

## 1. Confirmed: the data fields exist, and where

Source: `StranikS-Scan/WorldOfTanks-Decompiled` (branch `1.16`),
`source/res/scripts/common/items/vehicles.py`, class `VehicleDescriptor`.

The `__slots__` declaration for `VehicleDescriptor` includes three
fields relevant to this project:

- `visibilityCheckPoints` — a tuple of `Vector3` positions. One search
  hit shows one entry built from an expression combining hull Y
  position with a turret-local top offset, confirming these are
  derived from hull/turret geometry at descriptor-build time, not
  fetched live from a server.
- `observerPosOnChassis` — near-certainly one of the two "view range
  ports" from the public spotting-mechanics docs, hull-relative.
- `observerPosOnTurret` — the other view range port, turret-relative
  (this is the dynamic one that should track turret rotation).

**Why this is trustworthy**: this file lives under `scripts/common/`,
which is WoT's shared client+server code tree — meaning this data is
part of how the client independently derives vehicle stats the server
also uses, not something transmitted over the network. That matches
the architectural assumption the whole project depends on.

**Open item**: exact semantics of `visibilityCheckPoints` — confirm
it's a 6-tuple (matching the "6 visibility checkpoints" public
mechanics docs) and confirm the coordinate space (hull-local? some
mix?) for each entry. Current evidence only confirms one entry's
construction, not all six.

---

## 2. Confirmed: client-side pattern for getting WORLD-SPACE positions

This is the harder half of Phase 1, and it's now confirmed from
**multiple independent working mods**, not just one source.

### Pattern A — named hardpoint nodes on the compound model

Source: `StranikS-Scan/StranikS_Scan-mods`, `SimpleLogger` mod.

A live vehicle entity exposes an `appearance` object with a
`compoundModel`. Named parts/hardpoints can be looked up as nodes on
that compound model (e.g. a gun-fire hardpoint is fetched by string
name), and wrapping the returned node in the engine's `Matrix` type
exposes a `.translation` — i.e. **the confirmed pattern for turning a
named local hardpoint into a world-space position** is:

```
node = vehicle.appearance.compoundModel.node(<node_name>)
worldPos = Math.Matrix(node).translation
```

**Open item**: confirm whether `observerPosOnTurret` /
`observerPosOnChassis` / each `visibilityCheckPoints` entry corresponds
to an existing named node on the compound model (this pattern), or
whether they're raw local offsets that must instead be manually
transformed using Pattern B below. These may not be the same
mechanism — needs direct testing once Phase 2 prototyping starts.

### Pattern B — applying a raw local offset via the hull's world matrix

Source: `StranikS-Scan/StranikS_Scan-mods`, deprecated `Meter` mod.

For the player's own vehicle specifically, there's a direct API to get
the hull's current world matrix:

```
BigWorld.player().getOwnVehicleStabilisedMatrix()
```

wrapped again in `Math.Matrix(...)` to get a usable matrix object
(confirmed usage extracts yaw from it via a `.yaw`-style property, and
elsewhere in the same codebase similar matrices are applied to raw
local-offset vectors to project them into world space).

**This is very likely the mechanism for `observerPosOnChassis`** — a
hull-relative local point, transformed by the hull's own world matrix.
`observerPosOnTurret` would need the equivalent *turret* world matrix
instead (not yet located — see open items).

### Pattern C — per-component model matrices

Source: `Omegaice/WOTDecompiled`, `scripts/client/vehicle.py`.

The vehicle's `appearance` object also exposes a `modelsDesc` mapping
keyed by component name (hull, turret, etc.), where each entry has a
`model` with its own `.matrix` — a second, lower-level way to reach a
specific component's current world transform directly, without going
through named compound-model nodes. This may end up being the more
direct route to a turret world matrix for `observerPosOnTurret`.

---

## 3. Newly discovered: reusable community libraries (high value, not yet integrated)

- **`ktulho/XModLib`** — a shared code library used across several
  existing WoT mods. Directly relevant modules per its own description:
  a vehicle math module for model calculations and matrix
  transformations, a vehicle info class for entity-based info, and 3D
  geometry helpers (planes, bounding boxes). This is worth reading
  *before* hand-rolling our own `core/transform.py` — it may already
  solve exactly this problem, tested across many other mods and game
  versions.
- **`StranikS-Scan/StranikS_Scan-mods`** — a monorepo of many small,
  real, working WoT mods by the same author who maintains the
  decompiled-source repo. Extremely high-value as worked examples of
  exactly the kind of matrix/appearance API calls this project needs.
- **`chirimenmonster/wotmods-dispersionindicator`** — an existing mod
  that already surfaces live vehicle yaw/pitch/roll and position data
  in an on-screen panel. Directly relevant precedent for Phase 4's HUD
  panel (effective view range / camo % readout) — worth studying its
  UI-building approach even though its subject matter (dispersion, not
  spotting) differs.

---

## 4. Updated "where to look things up" priority list

Supersedes the priority list in `CONCEPT.md` / `AGENTS.md` — public
decompiled-source repos should be tried **before** running a local
Windows-only unpacker tool, since they update per game version and
require no Windows/`win32api` dependency at all:

1. `StranikS-Scan/WorldOfTanks-Decompiled` — pin to the branch matching
   `<GAME_VERSION>`
2. `StranikS-Scan/StranikS_Scan-mods` — worked-example mods using the
   real API
3. `ktulho/XModLib` — shared vehicle math/matrix helper library
4. `izeberg/wot-src` — faster-updated alternative if the above lags a
   very recent patch
5. `docs.wotstat.info`
6. Local `clientUnpacker.py` extraction — now a fallback, not the
   primary path, and only really needed if none of the above cover a
   specific version or a specific file

---

## 6. Session 2 update: live-entity access CONFIRMED

Sources: `aevitas/wotsdk` (`clientavatar.py`), `Omegaice/WOTDecompiled`
(`vehicle.py`, `vehicleappearance.py`), `StranikS-Scan/StranikS_Scan-mods`
(`Meter`), `python.hotexamples.com` aggregated snippets.

**`vehicle.typeDescriptor` is confirmed** — a live vehicle entity
directly exposes its `VehicleDescriptor` (the class from §1) as a
`.typeDescriptor` attribute. Confirmed across multiple independent
mods/files accessing things like `.typeDescriptor.gun[...]`,
`.typeDescriptor.turret[...]`, `.typeDescriptor.name`,
`.typeDescriptor.optionalDevices[...]`. This resolves the open item
from §5 about reaching the descriptor from a live entity.

**Getting the entity itself** — also confirmed, multiple equivalent
routes:
- `BigWorld.player().playerVehicleID` → the player's own vehicle ID
- `BigWorld.entity(vehicleID)` → fetch a specific entity by ID
- `BigWorld.entities` → dict-like collection of currently-known
  entities (only vehicles the client actually has data for — own
  team + spotted enemies, consistent with the server-authoritative
  model discussed earlier in this conversation)
- `BigWorld.player().onVehicleEnterWorld` → a callback/event hook that
  fires when a vehicle becomes available in the world — likely a
  cleaner lifecycle hook for initializing the overlay than polling
  every frame for entity readiness

**Useful lifecycle/state properties on a vehicle entity**: `.inWorld`,
`.isPlayerVehicle`, `.isAlive()`, `.isStarted` — worth using as guard
conditions before attempting any transform/overlay work in Phase 2/3.

### Hull world matrix — now confirmed via three independent routes

1. `vehicle.matrix` — base entity matrix property (simplest, seen used
   as a fallback when no vehicle filter is active)
2. `vehicle.filter.bodyMatrix` — when the entity's filter is a
   `BigWorld.WGVehicleFilter`, this is the preferred/more accurate
   source (filters typically smooth network-driven movement, so this
   is likely the "correct" one to prefer when available)
3. `vehicle.appearance.modelsDesc['hull']['model'].matrix` — confirms
   Pattern C from §2 directly: `'hull'` is a real, confirmed key in
   `modelsDesc`, and wrapping its `.matrix` gives the world matrix.

There's also an internal stabilization function,
`WoT.computeStabilisedVehicleMatrixU64(matrix, physicsData)`, which is
almost certainly what backs the previously-found
`getOwnVehicleStabilisedMatrix()` convenience method — good to know
both the low-level and convenience versions exist.

**Turret world matrix — still not directly confirmed**, but Pattern C's
`modelsDesc['hull']` being real makes it very likely there's an
equivalent `modelsDesc['turret']` entry following the same shape. This
is now a cheap, concrete thing to check by direct inspection (e.g. log
`vehicle.appearance.modelsDesc.keys()`) rather than something worth
more search time — diminishing returns on searching vs. just checking
it directly once Phase 2 prototyping starts.

### New reference mods found

- **`PolyacovYury/PYmods`**, `mod_ShowVehicle.py` — an existing mod
  that displays the player's own hull and turret while in sniper mode.
  This is architecturally close to Phase 2 of this project (rendering
  something related to the player's own vehicle geometry, gated to a
  specific context) and worth reading in full before writing
  `core/overlay.py`.
- **`PolyacovYury/PYmods`**, `mod_VMTFix.py` — "Vehicle Model
  Transparency Fix," addressing transparent elements not displaying
  correctly on the player's own vehicle. Possibly relevant if overlay
  markers interact oddly with the player's own vehicle model
  rendering — worth keeping in mind if Phase 2 hits transparency/z-order
  bugs.

---

## 7. Remaining open items before Phase 1 can be marked fully done

- [ ] Confirm all 6 `visibilityCheckPoints` entries' construction, not
      just the one seen so far, and confirm their coordinate space
- [ ] Confirm whether `observerPosOnChassis`/`observerPosOnTurret` map
      to named compound-model nodes (Pattern A) or need manual offset
      + matrix application (Pattern B/C) — hull-relative
      (`observerPosOnChassis`) is very likely Pattern B/C using the
      now-confirmed hull matrix; turret-relative
      (`observerPosOnTurret`) still needs the turret matrix confirmed
      below
- [ ] Confirm `modelsDesc['turret']` (or equivalent) exists and gives a
      usable world matrix the same way `modelsDesc['hull']` does — this
      is a direct-inspection task, not a research task, at this point
- [x] ~~Confirm how to get a live vehicle entity's `typeDescriptor`~~ —
      resolved in §6: `vehicle.typeDescriptor`
- [ ] Once the above are confirmed, run the actual Phase 1 prototype
      task from `TASKS.md` (log one checkpoint's world position each
      frame, sanity-check it in Garage) before moving to Phase 2


This is a comprehensive summary of the technical hurdles and breakthroughs we encountered during Phase 1 and Phase 2. You should append this to your `NOTES.md` to ensure future development (or AI agents) doesn't fall into the same "research loops."

---

# UPDATED NOTES.md (Post Phase 1 & 2)

## 8. Summary of Findings: Version 2.3.1.1 Specifics

### Data Location & "Ghost Attributes"
*   **The Findings:** Attributes like `visibilityCheckPoints` and `observerPos` exist as keys in the `TypeDescriptor` but return `None` on live vehicle entities.
*   **The Reason:** Modern clients use "Lazy Loading." Spotting data is not instantiated in the Python layer until the server triggers a spotting check.
*   **The Solution:** Use **Bounding Box Fallback**. The half-width (`trcp.x`) and half-length (`trcp.y`) from `descr.chassis.topRightCarryingPoint` are always available and are used by the engine to generate the 5 hull checkpoints if XML data is missing.

### Coordinate Space & Matrices
*   **The Findings:** In version 2.3.1.1, the matrices returned by `vehicle.appearance.compoundModel.node('hull')` and `node('turret')` are **already in World Space**.
*   **The Trap:** Multiplying these node matrices by `vehicle.matrix` (a standard practice in older versions) results in "Double Transformation," placing markers outside the map boundaries.
*   **The Formula:** `WorldPos = NodeMatrix.applyPoint(LocalOffset)`.

### Rendering & API Stability
*   **The Findings:** Internal models like `helpers/models/unit_cube.model` are often missing or have broken shaders in retail builds. 
*   **The Solution:** Use **Engine Debug Primitives**. 
    *   `BigWorld.wg_draw_box(min, max, color, drawOnTop)`
    *   `BigWorld.wg_draw_line(start, end, color)`
    *   These are Z-buffer independent (visible through walls) and require no external assets.
*   **GUI:** `GUI.Text` exists but is highly restricted. Properties like `.attached` do not exist. Control visibility using `GUI.addRoot(label)` and `GUI.delRoot(label)`.

### Mod Lifecycle
*   **The Trap:** The game often loads the mod twice (once for `.py`, once for `.pyc`), leading to "Double Toggling" where a single keypress turns the mod ON and then instantly OFF.
*   **The Solution:** Implement a **Singleton Guard** in `WotstatSpotting.py`:
    ```python
    if 'g_controller' not in globals():
        g_controller = None
    ```

---
