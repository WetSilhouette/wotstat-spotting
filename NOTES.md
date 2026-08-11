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

---

## 9. Session 3: probe bug fix + closure test, pending manual run

**Found a real bug in the old `phase1_probe.py`**: `turr_xml` was only
assigned inside `if section.has_key('turrets0')`, but was referenced
unconditionally afterward for the `observerPos` check. When that branch
didn't fire, this threw `NameError`, which the outer `try/except`
swallowed into a generic `"Probe CRASHED: ..."` log line with no useful
detail. This is a plausible explanation for confusing failures during
the earlier (lost/failed) Phase 2 attempt — worth remembering: **the old
probe's crash logs may not reflect real API failures**, just this bug.

`core/phase1_probe.py` was rewritten (still throwaway diagnostic code,
not shipped functionality) to fix this and directly attack every
remaining open item from §7 in one pass:

- Reads hull + turret `visibilityCheckPoints` and `observerPos` from the
  vehicle's own item_defs XML (same lazy-loading workaround as before),
  now logging **every** entry (not just implicitly the first) plus a
  running total, to settle the "is it really 6" question.
- Tries `child.asVector3` on each XML entry (new — the old probe only
  ever logged `.asString`); falls back to logging the raw string if that
  accessor doesn't exist, so the run still yields usable data either way.
  `# TODO(api-verify)`: `.asVector3` is a guess based on the standard
  BigWorld `DataSection` accessor family (`.asString`/`.asFloat`/
  `.asVector3`/...), not yet confirmed against this game version.
- Dumps `vehicle.appearance.modelsDesc.keys()` and every entry's
  `['model'].matrix` world position — this directly answers whether
  `modelsDesc['turret']` exists alongside the already-confirmed
  `modelsDesc['hull']`.
- Searches compound-model nodes `hull`, `turret`, `turret0`, `gun`,
  `HP_turretJoint`, `HP_gunJoint` (expanded from the original 4) and
  logs each one found/not-found.
- Projects every parsed local offset into world space via
  `matrix.applyPoint(localOffset)` (the formula from §8) using whichever
  hull/turret matrix was found (node search preferred, `modelsDesc` as
  fallback), and logs the result — this is the actual "sanity check
  against known tank geometry" step `TASKS.md` Phase 1 asks for.

Also fixed in `WotstatSpotting.py`: added the singleton/double-init
guard described in §8 (`g_probeStarted` global flag), since without it
a double module load would run the whole probe twice and interleave
duplicate log output, which would make the log genuinely hard to read
correctly.

Also fixed: `utils/combat.py` was a typo — `TASKS.md` Phase 0 calls for
`utils/compat.py`. Renamed via `git mv`, no content yet (still an empty
placeholder per the original Phase 0 task).

Verified locally (no game client involved): Python 2 syntax
(`python2 -m py_compile`) passes on the changed files, and
`./build.sh -v 0.0.3 -d` packages a `.wotmod`/`.mtmod` successfully
end-to-end. **Not yet verified**: whether the probe's API calls actually
work at runtime — that requires the game client, which this environment
doesn't have.

### What to do next (manual, in the game client)

1. `./build.sh -v <next-version> -d`, install to
   `Tanki/mods/<GAME_VERSION>/`, launch, open Garage with any vehicle
   selected.
2. Watch the log for the `===== Phase 1: Deep Extraction Started =====`
   block (fires automatically ~2s after Garage loads, via
   `poll_for_probe`).
3. Report back (or paste into this file under a new dated entry):
   - Did `hull visibilityCheckPoints` and `turret visibilityCheckPoints`
     both print entries, and do they sum to 6?
   - Did `asVector3 FAILED` appear for any entry? If so, the raw-string
     fallback lines are what we fall back to parsing instead.
   - What did `modelsDesc keys:` print — does `'turret'` appear?
   - Which of the `node[...]` lines say `NOT FOUND` vs. print a
     plausible-looking world position?
   - Do the `World-space projection` lines print sane coordinates (i.e.
     roughly on/near the tank, not far off-map — that's the
     "double transformation" trap from §8), or do they error out?
4. Once all of §7's open items are answered from real log output, mark
   Phase 1 fully done and move to Phase 2 (`core/geometry.py`,
   `core/transform.py`) using the *now-confirmed* accessor names instead
   of the current guesses.

---

## 10. Session 3, first real in-game log — Pattern A confirmed, XML schema assumption wrong

Ran during a battle load (log shows `BattleSpace()`, `OwnVehicle
initialUpdate`, `battleVehicleMarkersApp.swf` — not Garage). Vehicle:
`china:Ch29_Type_62C_prot`.

**CONFIRMED — the hard problem from Phase 1 is solved:**
`vehicle.appearance.compoundModel.node(name)` wrapped in `Math.Matrix(...)`
returns plausible, sane world-space positions for **all** of `hull`,
`turret`, `gun`, `HP_turretJoint`, `HP_gunJoint` (`turret0` correctly
not found — `turret` is the real name). Concretely:

```
node[hull]           world pos: (0.000, 0.909, 0.000)
node[turret]         world pos: (0.000, 1.410, 0.081)
node[gun]            world pos: (0.002, 1.749, 1.105)
node[HP_turretJoint] world pos: (0.000, 1.410, 0.081)
node[HP_gunJoint]    world pos: (0.002, 1.749, 1.105)
```

This is Pattern A from section 2, now confirmed end-to-end on a live
entity, not just from reading other mods' source. **This is the
recommended approach going into Phase 2** for both the hull and turret
world matrices — no need for `modelsDesc` or raw hull-matrix + manual
offset math.

**DEAD — drop Pattern C:** `vehicle.appearance.modelsDesc` does not
exist on this game version's `CompoundAppearance`
(`'CompoundAppearance' object has no attribute 'modelsDesc'`). The
external source that described `modelsDesc['hull']` was for an older
client. Don't spend more time on this pattern.

**NEW PROBLEM — raw XML schema assumption from section 1 appears wrong
(or this vehicle is atypical):** `section.has_key('hull')` and
`section.has_key('turrets0')` both returned `False` with no error (the
XML file itself opened fine at
`scripts/item_defs/vehicles/china/Ch29_Type_62C_prot.xml`) — so
`visibilityCheckPoints`/`observerPos` never got parsed, count=0 across
the board. The `StranikS-Scan/WorldOfTanks-Decompiled` `1.16` branch
class definition this was based on may not match the live client's
actual per-vehicle XML layout, or checkpoints for this specific vehicle
aren't hand-authored at all — this looks like the "Bounding Box
Fallback" scenario predicted in section 8 (engine derives hull
checkpoints from `descr.chassis.topRightCarryingPoint` when XML data is
absent), which is exactly why this session's probe update added a
direct dump of `descr.chassis.topRightCarryingPoint` plus a raw
`section.keys()` dump of the actual XML schema, and a re-check of
`descr.visibilityCheckPoints`/`observerPosOnChassis`/
`observerPosOnTurret` directly (the earlier "Ghost Attribute" finding
was from Garage; this run is the first one during an actual battle,
where the lazy-loading theory says they might resolve).

**Not yet answered — rerun needed with the updated probe** (this
session's `phase1_probe.py` changes came *after* the log above, so none
of the following showed up in it yet):
- What are the real top-level keys in the per-vehicle XML root, and in
  the first `turrets0` entry?
- Does `descr.chassis.topRightCarryingPoint` return real values (Bounding
  Box Fallback theory)?
- Do `descr.visibilityCheckPoints` / `descr.observerPosOnChassis` /
  `descr.observerPosOnTurret` resolve to non-`None` now that this is a
  battle context instead of Garage?

**Also worth clarifying**: this test ran during a battle, not Garage —
worth confirming whether it was a Training Room (fine) or a competitive
mode (not fine to leave unrestricted going forward, since
`utils/restriction.py` has no gating logic yet — this is a Phase 3 gap,
not a bug in this session's changes, but worth being deliberate about
which modes get used for manual testing until the gate exists).

---

## 11. Session 3, second log (Training Room, confirmed) — schema mystery resolved, new dead end found

Confirmed Training Room. Same vehicle. This run used the updated probe
from section 10, so it directly answers the outstanding questions.

**CONFIRMED — `visibilityCheckPoints`/`observerPos` are not a nesting
problem, they genuinely don't exist in this vehicle's XML.** The dumped
root keys are:

```
['xmlns:xmlref', 'crew', 'supplySlots', 'postProgressionTree',
 'customRoleSlotOptions', 'speedLimits', 'invisibility',
 'optDevsOverrides', 'repairCost', 'camouflage', 'hull', 'chassis',
 'turrets0', 'engines', 'fuelTanks', 'radios',
 'clientAdjustmentFactors', 'crewXpFactor', 'physics', 'effects',
 'emblems']
```

`hull` and `turrets0` **are** present at the top level (so the earlier
`has_key` check itself works fine) — the `hull` section was
successfully opened, it simply has no `visibilityCheckPoints` or
`observerPos` child. Same for the `turrets0[0]` section, whose full key
list is:

```
['userString', 'tags', 'level', 'price', 'notInShop', 'armor',
 'primaryArmor', 'weight', 'maxHealth', 'rotationSpeed',
 'turretRotatorHealth', 'circularVisionRadius',
 'surveyingDeviceHealth', 'guns', 'models', 'hitTester', 'gunPosition',
 'wwturretRotatorSoundManual', 'physicsShape', 'customizationSlots',
 'customization', 'camouflage']
```

**Conclusion: this game version's item_defs XML does not hand-author
spotting checkpoints/observer positions at all.** The
`StranikS-Scan/WorldOfTanks-Decompiled` `1.16` reference this project's
Phase 1 started from is stale on this specific point for the current
client. Section 1's "confirmed" claim needs a correction flag — the
*fields exist as `VehicleDescriptor.__slots__`* is still presumably
true (that's a Python class definition, separate from the XML content),
but *this vehicle's XML source data for them* does not exist.

**CONFIRMED — Bounding Box Fallback is real and returns usable data:**

```
descr.chassis.topRightCarryingPoint: (1.20235, 1.74121)
```

A real `(halfWidth, halfLength)`-shaped 2-vector, not `None`. This is
the first concrete, non-`None`, non-hardpoint number this project has
gotten for chassis extents, and matches section 8's fallback theory.

**DEAD END (for now) — the "Ghost Attributes" don't resolve in battle
either:** `descr.visibilityCheckPoints`, `descr.observerPosOnChassis`,
`descr.observerPosOnTurret` were all still `None`, checked ~1 second
after spawning in a Training Room. The "lazy loading, resolves once the
server triggers a spotting check" theory from section 8 is not
confirmed by this — either it needs an actual spotting event to occur
first (not just being alive in battle), or these attributes are never
populated client-side for the owning player's own vehicle at all (there
would be no reason for the server to send a player their own spotting
checkpoints via this mechanism — it's plausible this attribute path is
specifically for *processing* spotting checks against other vehicles,
not for self-inspection). Don't keep polling this path hoping it
resolves; it's not the way to get our own vehicle's checkpoints.

**Compound node search — unchanged and stable across both runs**, same
values as section 10. Confirms Pattern A is solid, not a one-off fluke.

### Updated §7 status

- [x] Confirm all 6 `visibilityCheckPoints` entries — **answered
      differently than expected**: there are no hand-authored entries
      to count. Checkpoints must be derived (bounding-box math), not
      read.
- [x] `observerPosOnChassis`/`observerPosOnTurret` mapping — **answered**:
      neither raw XML nor `typeDescriptor` exposes them on this client.
      Needs a derived/fallback approach or a different data source
      entirely (see open item below).
- [x] `modelsDesc['turret']` — **moot**, `modelsDesc` doesn't exist on
      this client at all (section 10). Pattern A (node lookup) is the
      confirmed approach for both hull and turret world matrices.
- [ ] **NEW open item**: find the actual formula/documentation for
      deriving the 5 hull checkpoints from `topRightCarryingPoint`
      (half-width/half-length), and find where the 2 view-range-port
      local offsets should come from given neither XML nor
      `typeDescriptor` has them on this client. This is now the one
      real blocker left before Phase 2 can start for real — likely
      needs public spotting-mechanics documentation (community wikis)
      rather than more client-side probing, since the client-side data
      sources have been exhausted.
- [ ] Still open: whether the turret-mounted checkpoint(s)/port track
      turret rotation live via the same `node('turret')` matrix, or
      need the `gun`/`HP_gunJoint` matrix instead — can't test until
      the local offsets themselves are known.

---

## 12. Session 3 web research — the exact engine formula, CONFIRMED BY CODE

Two independent code sources, not just descriptions:
- This project's own client, decompiled from the shipped
  `scripts.pkg` (`scripts/common/items/vehicles.pyc`).
- Public: `StranikS-Scan/WorldOfTanks-Decompiled`, branch `1.42`,
  `source/res/scripts/common/items/vehicles.py`, `VehicleDescriptor.__initAttrs__`.

Both show identical logic. **This settles why `typeDescriptor.visibilityCheckPoints`/`observerPos*` are `None` on the client**: the assignment is guarded by `if IS_CELLAPP or IS_UE_EDITOR:` — i.e. this whole block only runs server-side (cell app) or in the UE editor, never on a live game client. Section 11's "dead end" conclusion is now explained, not just observed.

```python
hullPos = self.chassis.hullPosition
hullBboxMin, hullBboxMax, _ = self.hull.hitTester.bbox
turretPosOnHull = self.hull.turretPositions[0]
turretLocalTopY = max(hullBboxMax.y, turretPosOnHull.y + self.turret.hitTester.bbox[1].y)
gunPosition = self.turret.gunPosition
gunPosOnHull = turretPosOnHull + gunPosition
hullLocalCenterY = (hullBboxMin.y + hullBboxMax.y) / 2.0
hullLocalPt1 = Vector3(0.0, hullLocalCenterY, hullBboxMax.z)
hullLocalPt2 = Vector3(0.0, hullLocalCenterY, hullBboxMin.z)
hullLocalCenterZ = (hullBboxMin.z + hullBboxMax.z) / 2.0
hullLocalPt3 = Vector3(hullBboxMax.x, gunPosOnHull.y, hullLocalCenterZ)
hullLocalPt4 = Vector3(hullBboxMin.x, gunPosOnHull.y, hullLocalCenterZ)
self.visibilityCheckPoints = (
 Vector3(0.0, hullPos.y + turretLocalTopY, 0.0),   # 1: highest point, on centreline
 hullPos + gunPosOnHull,                            # 2: gun mount point
 hullPos + hullLocalPt1,                            # 3: front face centre, hull mid-height
 hullPos + hullLocalPt2,                            # 4: rear face centre, hull mid-height
 hullPos + hullLocalPt3,                            # 5: right face centre, at GUN height
 hullPos + hullLocalPt4)                            # 6: left face centre, at GUN height
self.observerPosOnChassis = Vector3(0, hullPos.y + turretLocalTopY, 0)
self.observerPosOnTurret = gunPosition
```

Notes on reading this:
- **Not** "4 bbox corners + centre" as guessed in section 10. It's:
  top-centre (tallest point), gun mount, front/rear face centres at
  **hull mid-height**, left/right face centres at **gun height** — the
  left/right pair intentionally uses a different height than
  front/rear.
- `observerPosOnChassis` == checkpoint 1 (top-centre) exactly — not a
  "commander's hatch" position, just the tallest collision point on the
  centreline.
- `observerPosOnTurret` == `turret.gunPosition` verbatim, in
  **turret-local** space — confirms the TASKS.md assumption that this
  port tracks turret rotation (project via the `turret` node matrix,
  not `hull`).
- All the inputs (`chassis.hullPosition`, `hull.hitTester.bbox`,
  `hull.turretPositions[0]`, `turret.hitTester.bbox`,
  `turret.gunPosition`) are **separate typeDescriptor sub-fields from
  the ones that were `None`** (section 11) — these are not
  server-gated, they should be readable client-side. Untested by this
  project's own code yet — that's the next probe run.

**Known gotcha (from decompiled `model_assembler.pyc`, not yet
exercised by our own code)**: `hull.hitTester.bbox` /
`turret.hitTester.bbox` are `None` in Garage until collisions are set
up via `model_assembler.setupCollisions(vehicle.typeDescriptor,
vehicle.appearance.collisions)`. In battle, the appearance already
populates it (consistent with section 11's successful
`topRightCarryingPoint` read in a Training Room). `# TODO(api-verify)`
on the exact `setupCollisions` call — sourced from decompiled bytecode,
not yet run by this project.

**Existing prior art**: `wotstat/wotstat-debug-utils`'s
`SpottingUtil.py` (`res/scripts/client/gui/mods/wotstatDebugUtils/coreUtils/spottingUtils/SpottingUtil.py`)
already implements this exact reconstruction (via `getVehicleVisibilityBbox`
+ `getMaskSpotPoints`) for its own debug overlay, including the dynamic
turret/gun matrix composition for the rotating port and the
`turretAndGunAngles.getTurretYaw()/getGunPitch()` fallback when
`appearance.turretMatrix`/`gunMatrix` are unavailable. Worth reading
directly once Phase 2 implementation starts, as a second working
reference alongside this formula — but per this project's `AGENTS.md`/
`CONCEPT.md` convention, borrow the *pattern*, write our own
implementation into `core/geometry.py` (pure math, matches this
project's existing separation of pure-logic vs. game-API-glue code) and
`core/transform.py` (the BigWorld glue), not a copy-paste.

**Web search turned up nothing else**: no wiki, blog, or
`docs.wotstat.info` page documents this exact geometry publicly —
community "6 spotting points" writeups are conceptual only. The
decompiled engine source and `wotstat-debug-utils` are the only two real
sources.

### Next: validate this formula live before it becomes real Phase 2 code

`phase1_probe.py` was rewritten again to compute the 6 checkpoints + 2
ports using this exact formula against a live vehicle, project them
via the confirmed `node('hull')`/`node('turret')` world matrices, and
log the result *repeatedly* (every 3s, up to 20 times) instead of once
— so hull/turret rotation can be observed across log lines, closing the
last unchecked box in TASKS.md Phase 1 ("rotate the turret, confirm the
dynamic port's position changes; confirm the static checkpoints don't").
The old XML-parsing and ghost-attribute diagnostics were removed from
the probe — both questions are now conclusively answered, so they were
just noise going into a repeating log.

**Ask**: run this in Garage this time if possible (exercises the
untested `setupCollisions` fallback), and try rotating the hull/turret
during the ~60-second logging window. Once the numbers look sane and
the turret-tracking port visibly moves while the hull checkpoints don't,
Phase 1 is fully done and this logic moves into `core/geometry.py` +
`core/transform.py` for real.

---

## 13. Session 3, live validation run — formula CONFIRMED CORRECT, Garage still broken

Training Room, same vehicle, python.log captured across the full
~60s/20-iteration window (`python.log` lines 644-917 in the client
install).

**Garage/hangar does NOT work** (matches the user's own report): the
first iteration fired ~2s after "vehicle ready", while
`hull.hitTester.bbox`/`turret.hitTester.bbox` were still `None`, and the
`setupCollisions` fallback failed outright: `No module named
model_assembler` — the import path guessed from decompiled bytecode is
wrong (wrong module name or wrong package path; needs research, not
guessing again). That said: **in this Training Room run, the bbox
became available on its own 3 seconds later**, with no fallback needed
— so battle contexts seem to self-populate collisions shortly after
spawn, but Garage apparently does not (no battle-load pipeline to
trigger it), so this import bug is a real blocker specifically for
Garage, which is Phase 2's primary target per `CONCEPT.md` (Phase 2 is
literally titled "Own-Tank Checkpoint/Port Visualization (**Garage**)").

**Once bbox was available, every number came out sane and internally
consistent** — several independent cross-checks all passed:
- `front`/`rear` checkpoint z-offsets from hull center were nearly
  equal and opposite (2.410 vs 2.406) — confirms the hull bbox is
  symmetric and the formula's min/max usage is correct.
- `right`/`left` checkpoint x-offsets were nearly equal and opposite
  (-0.838 vs +0.844) — same symmetry check, x-axis.
- `observerPosOnChassis` exactly equals `checkpoint[top]` on every
  iteration — matches the formula (`Vector3(0, hullPos.y +
  turretLocalTopY, 0)` computed twice) being literally the same value
  both times, as intended.
- `observerPosOnTurret`, computed purely from the formula
  (`turretMatrix.applyPoint(gunPosition)`), landed within ~0.001 units
  of `node('gun')`'s own directly-queried world position on every
  iteration — two independently-derived numbers agreeing almost
  exactly. Strong confirmation both the formula and the node-matrix
  approach are correct.

**Important subtlety, only discoverable by testing live rotation, not
by reading the formula**: at iteration 9 (18:42:06), the vehicle's gun
position changed (turret/gun rotated) while the hull position stayed
fixed. Result:
- `observerPosOnTurret` updated immediately to track the new gun
  position (as expected — it's projected via the live `turret` node
  matrix each call).
- **`checkpoint[gunMount]` did NOT change** — it stayed at its
  previous, pre-rotation value, even though "gunMount" sounds like it
  should track the gun.

This is correct, not a bug: `checkpoint[gunMount]` is computed as
`hullPos + gunPosOnHull` where `gunPosOnHull = turretPosOnHull +
gunPosition`, using the **static, neutral-pose** `gunPosition` from
`typeDescriptor` (a per-vehicle design-time constant, not a live
value), and the whole thing is projected through the **hull** matrix
only. So **5 of the 6 visibility checkpoints — including the
"gunMount" one — are rigidly hull-relative and never track live turret
rotation.** Only `observerPosOnTurret` (the second view-range port)
actually tracks turret rotation live, exactly as `TASKS.md` guessed
("one port is static/hull-relative, the other tracks the gun mount,
dynamic with turret rotation") — but the guess undersold it: it's not
just one *port* that's static, it's the entire 6-checkpoint set. This
matters for Phase 2/4: don't try to make checkpoint markers rotate with
the turret, only the `observerPosOnTurret` marker should.

Later iterations (10+) show the vehicle actually driving — hull,
turret, and gun world positions all shift together by 10-25 units
between 3s samples, and all 6 checkpoints + `observerPosOnChassis` move
in lockstep with the hull, while `observerPosOnTurret` continued
tracking gun/turret independently. This is the expected rigid-body
behavior and closes out the "does it track a moving vehicle correctly"
question too.

### Phase 1 status: DONE for battle/Training Room contexts

Every open item in section 7 is now answered with live, validated data.
**Remaining before Phase 2 can start in Garage** (the actual primary
target): fix the `model_assembler` import — needs a quick research
pass, since guessing a second time already failed once.

---

## 14. Session 3 web research — Garage fix, CONFIRMED against this exact client version

Found the decompiled-source branch that matches this project's actual
client build exactly: `StranikS-Scan/WorldOfTanks-Decompiled`, branch
`2.3.1_EU` (`version.xml` = `v.2.3.1.1 #910`) — also confirmed directly
against this machine's own `res/packages/scripts.pkg`. Use this branch
for any future decompiled-source lookups on this project; earlier
sections referencing `1.16`/`1.42` were for other versions and can be
stale.

**Fix 1 — wrong import path (this is the whole bug).** The correct
import is:

```python
from vehicle_systems import model_assembler
```

not top-level `model_assembler`. Source:
`source/res/scripts/client/vehicle_systems/model_assembler.py`:

```python
def setupCollisions(vehicleDesc, collisions):
    hitTestersByPart = {TankPartNames.CHASSIS: vehicleDesc.chassis.hitTester,
     TankPartNames.HULL: vehicleDesc.hull.hitTester,
     TankPartNames.TURRET: vehicleDesc.turret.hitTester,
     TankPartNames.GUN: vehicleDesc.gun.hitTester}
    for partName, hitTester in hitTestersByPart.iteritems():
        partID = TankPartNames.getIdx(partName)
        hitTester.bbox = collisions.getBoundingBox(partID)
```

**Why battle self-populates this and Garage doesn't**: in
`client_common/vehicle_appearance/common_tank_appearance.py`,
`CommonTankAppearance._connectCollider` ends by calling
`model_assembler.setupCollisions(self.typeDescriptor, collisions)`.
`client/gui/hangar_vehicle_appearance.py`'s
`HangarVehicleAppearance._connectCollider` does **not** — it only calls
`collisions.connect(...)`. That one missing call is the entire root
cause of section 13's Garage failure — nothing else is different.

**Fix 2 — vehicle detection is also wrong for Garage, separate bug.**
`WotstatSpotting.py`'s `poll_for_probe` currently gates on
`hasattr(player, 'getOwnVehicleStabilisedMatrix')`, which is battle/
Avatar-only — in Garage, `BigWorld.player()` is a different class
without this method, so the probe likely never fires at all in Garage,
independent of the collision bug above. The confirmed Garage-side
vehicle entity type is `HangarVehicle` (from
`scripts/client/gui/...` — surfaced via `BigWorld.entities.values()`,
same collection used for battle entities), not reachable through
`player.playerVehicleID`.

**Confirmed existing prior art**: `wotstat/wotstat-debug-utils`
already solves both problems, in two files
(`coreUtils/mainUtils/BboxUtil.py` and
`coreUtils/spottingUtils/SpottingUtil.py`, both with an identical
`updateHangarVehicle` block):

```python
hangarSpace = dependency.descriptor(IHangarSpace)
...
isInHangar = self.hangarSpace and self.hangarSpace.spaceID is not None
if not isInHangar: return
targetVehicles = [entity for entity in BigWorld.entities.values()
                  if isinstance(entity, ClientSelectableCameraVehicle if self.showAny else HangarVehicle)
                  and entity.appearance]
for vehicle in targetVehicles:
  if vehicle.typeDescriptor.hull.hitTester.bbox is None and vehicle.appearance.collisions is not None:
    model_assembler.setupCollisions(vehicle.typeDescriptor, vehicle.appearance.collisions)
```

Also notes a *third* difference worth remembering for Phase 2/4 (not
yet relevant to our node-matrix approach, which is separate from this):
hangar appearance has no `turretMatrix`/`gunMatrix` attribute the way
battle appearance does; that mod falls back to
`vehicle.appearance.turretAndGunAngles.getTurretYaw()`. Our project
uses `compoundModel.node('turret')` instead (Pattern A, section 10),
which is a different, already-battle-confirmed mechanism — untested in
Garage specifically, but no reason yet to think it's affected by this
particular gap.

### Applied to this project

`phase1_probe.py` and `WotstatSpotting.py` updated this session:
- `_ensureHullTurretBbox` now imports `from vehicle_systems import
  model_assembler` (was bare `import model_assembler`), and only
  attempts the call when `vehicle.appearance.collisions is not None`
  (guards the same case `BboxUtil.py` guards).
- Vehicle detection now tries the existing battle path first, then
  falls back to scanning `BigWorld.entities.values()` for an entity
  whose class name is `'HangarVehicle'` (duck-typed by name rather than
  importing the class, to keep this throwaway probe minimal — `#
  TODO(api-verify)`: revisit with a real import once this moves into
  `core/transform.py`).

**Ask**: rebuild and retest in Garage. If it works, Phase 1 is fully
closed for both contexts and this logic (plus the confirmed formula
from section 12) is ready to move into `core/geometry.py` +
`core/transform.py` as real Phase 2 code.

---

## 15. Session 3, Garage retest — deprioritized, real cause identified

The Garage retest log did **not** actually exercise the Fix 1/Fix 2
code above. Timeline from the captured `python.log`:

```
18:54:00.188  last successful probe fire (still Training Room)
18:54:01.302  Avatar.leaveArena (leaving the Training Room)
18:54:27.979  HANGAR READY
18:54:47.762  "Probe loop finished after 20 iterations"  <- no probe log between 18:54:01 and here
```

The repeating probe loop (`_repeatingProbe` in `WotstatSpotting.py`)
locks onto a single `vehicleID` when it starts and never goes back to
`poll_for_probe()` to look for a *new* vehicle if the game context
changes mid-loop. Once the Training Room ended, `BigWorld.entity(oldID)`
just returned nothing useful for the remaining iterations, and the loop
silently ran out its fixed 20-iteration budget in Hangar without ever
attempting a probe there. **This is a bug in this project's own polling
architecture, not evidence that the Garage collision-setup fix (section
14) doesn't work** — the fix was never actually tested.

**Decision (explicit user instruction): stop pursuing Garage support
for now, focus exclusively on battle/Replay/Training Room.** Applied to
code this session:
- `findOwnVehicle()` reverted to battle-only (`player.playerVehicleID`
  path only); the `HangarVehicle` entity-scanning branch was removed.
- `_ensureHullTurretBbox()` reverted to a plain getter — the
  `model_assembler.setupCollisions` fallback (section 14) was removed
  since it's unvalidated and no longer in scope.

If Garage support is revisited later, section 14's findings (correct
import path `from vehicle_systems import model_assembler`, the
`HangarVehicle` entity type, the `IHangarSpace`/`BboxUtil.py`/
`SpottingUtil.py` reference pattern) are still believed correct — they
just were never actually exercised end-to-end due to the polling bug
above, not disproven. The polling-restart bug itself would also need
fixing (e.g. have `_repeatingProbe` fall back to `poll_for_probe()` when
the tracked vehicle disappears) before a real Garage retest would be
meaningful.

### Phase 1 status: DONE (scope: battle/Replay/Training Room)

All of section 7's original open items, plus the formula validation
from sections 12-13, are answered and confirmed with live data. Ready
to move this logic into `core/geometry.py` (pure math) +
`core/transform.py` (BigWorld glue) for Phase 2, scoped to
battle/Replay/Training Room only. Garage is explicitly out of scope
until deliberately revisited.

---

## 16. Session 3 — Phase 2 data layer: geometry.py + transform.py written

Migrated the confirmed logic out of the throwaway `phase1_probe.py`
into real modules, matching the split `AGENTS.md` calls for ("keep
local checks ... in files with no game-API imports so it's testable in
isolation; keep game-API glue code separate"):

- **`core/geometry.py`** (new): pure Python, zero game-API imports.
  `computeLocalCheckpoints(...)` is the formula from section 12, taking
  and returning plain `(x, y, z)`-indexable points instead of
  `Math.Vector3` so it has no dependency on the game client at all.
  Sanity-checked directly with `python3` (bbox symmetry ->
  front/rear and left/right checkpoint pairs are mirror-symmetric;
  `observerOnChassis == checkpoint['top']`; `gunMount` is the plain sum
  of hull/turret/gun local offsets) — all passed. This is the "pure-
  logic code... verified independently of the game client" `AGENTS.md`
  asks for.
- **`core/transform.py`** (new): the BigWorld glue. `findOwnVehicle()`
  (moved from the probe, battle-only per section 15),
  `getNodeMatrices()` (section 10's confirmed `compoundModel.node()` +
  `Math.Matrix()` pattern), `getHullTurretBbox()` (section 13's
  self-populating bbox, no Garage fallback), and
  `computeWorldCheckpointsAndPorts(vehicle)` — the single entry point
  Phase 2 rendering code should call, returning `(checkpoints, ports)`
  dicts of world-space `Math.Vector3`, or `None` if collision data
  isn't ready yet (not an error condition, just "retry next tick").
- **`core/phase1_probe.py`** gutted down to a thin logging wrapper
  around `transform.computeWorldCheckpointsAndPorts()`, per
  `AGENTS.md`'s own instruction for this file ("delete or gut ... once
  Phase 1 is marked fully confirmed"). `WotstatSpotting.py` needed no
  changes — it already only calls `phase1_probe.findOwnVehicle()` /
  `.runManualProbe()`, which now just delegate to the real modules.

Verified: `python2 -m py_compile` on all four touched files, and a full
`./build.sh -v <n> -d` packaging pass.

**Re-verified against a live vehicle (Training Room) — migration
confirmed correct, no behavior change from the pre-migration probe:**
- `port['chassis']` exactly equals `checkpoint['top']` on every sample.
- At one sample the turret rotated while the hull stayed still:
  `port['turret']` moved, all 6 checkpoints stayed frozen — same
  hull-vs-turret split confirmed in section 13.
- Later samples show the vehicle driving: all 6 checkpoints + both
  ports shift together, correct rigid-body behavior.
- One harmless "not ready yet" line right after spawn (bbox not
  populated for the first tick, as expected), then clean output with no
  errors or crashes for the rest of the run.

**Phase 2 data layer is done and confirmed working.** Next up is
`core/overlay.py` (rendering), per the notes above.

---

## 17. Session 4 — rendering: DebugDrawer, not wg_draw_box (that claim was wrong)

Before writing `core/overlay.py`, checked whether `wotstat-vegetation`
(this project's own explicit pattern reference) actually uses
`wg_draw_box`/`wg_draw_line` per the earlier "Post Phase 1 & 2" note in
this file — **it does not**. Its real rendering uses two different
things, neither a good fit here:
- `gui.debugUtils` (`gizmos`/`drawer`) — optional import from the
  *separate* `wotstat-debug-utils` mod, `None` if that mod isn't
  installed. Can't be a primary dependency for this project's core
  feature.
- Actual spawned `BigWorld.Model` instances via `player.addModel()` +
  `BigWorld.Servo(matrix)` for its always-on colliders — real, working,
  but needs real `.model`/`.visual` assets and a whole caching pipeline
  (`VegetationColliderCache`), overkill for simple point markers.

Given `wg_draw_box`/`wg_draw_line` had never been independently
verified (that note came from an earlier session's own unverified
claims, which the user asked to disregard), did a fresh research pass
against the decompiled `2.3.1_EU` source and this machine's actual
retail binary rather than trust it again.

**Found: `DebugDrawer`, a native (compiled-in, no `.py` source) Python
module.** Confirmed two ways:
- WG's own shipped script calls it —
  `vehicle_systems/components/vehicle_to_camera_alignment_components.py`:
  ```python
  import DebugDrawer
  DebugDrawer.DebugDrawer().cube().zTest(False).wireframe(True).colour(4278255360L).position(aabbCenter).scale(vehicleSize)
  DebugDrawer.DebugDrawer().sphere().zTest(False).wireframe(True).colour(4294967040L).position(frameCenter).scale(Math.Vector3(0.2, 0.2, 0.2))
  DebugDrawer.DebugDrawer().line().zTest(False).colour(4294967040L).points([aabbCenter, frameCenter])
  ```
- The full registered API is visible via C++ RTTI symbols in this
  machine's actual retail `WorldOfTanks.exe`: factories
  `line, bullet, cube, rgbCube, sphere, cone, cylinder, sector, label,
  rect2D, star, axes, frustum`; builder methods `wireframe, zTest,
  zWrite, blendMode, doubleSided, colour, position, rotation, scale,
  transform, aabb`. Fluent, returns self, no `lifetime`/persistence
  method — matches the immediate-mode, called-every-tick usage in WG's
  own example.

**Refuted the earlier "helpers/models/unit_cube.model often
missing/broken in retail" claim directly**: scanned all 115 `.pkg`
files in this install's `res/packages/` for `helpers/models` — zero
hits (method validated by successfully finding an unrelated known-good
path in the same scan). That code path is simply dead in retail, not
"sometimes broken." Two *different* primitive models genuinely do ship,
in `misc.pkg`, as a fallback if `DebugDrawer` doesn't pan out:
`system/models/fx_unit_sphere.model` and
`objects/misc/bbox/unit_cube_1m_proxy.model`.

**Also checked `wotstat-debug-utils`'s own gizmo internals** (not to
depend on the mod, but to see its technique): it does not use 3D
geometry at all. Its `Box`/markers are 2D — 8 world points pushed to a
Cohtml overlay via `GUI.WGMarkerPositionController`, rendered by
TypeScript in screen space. Worth remembering as a fallback pattern if
`DebugDrawer` turns out not to render in a retail build, but not
preferred (loses true 3D depth/occlusion behavior).

**Honest open item, not yet resolved**: `DebugDrawer`'s only found
caller in the decompile sits behind a `g_alignmentCameraVisuals.enabled`
flag inside a `CGF.Domain.ClientEditor`-namespaced file, and BigWorld
engines sometimes stub debug-draw calls outside dev/editor builds. It
is **not yet confirmed to actually render anything in this retail
client** — that's what the first live test of `core/overlay.py` is for.
If nothing appears, fall back to `BigWorld.Model('objects/misc/bbox/unit_cube_1m_proxy.model')`
(confirmed shipped) before trying the 2D-projection route.

### Applied: core/overlay.py + real toggle wiring

- **`core/overlay.py`** (new): `render(checkpoints, ports)` draws a
  small wireframe cube per point via `DebugDrawer`, distinct colors for
  checkpoints vs. ports. Immediate-mode — must be called every frame
  while active, matching WG's own usage pattern. Color channel order
  (`colour()` takes a packed int) is unconfirmed — marked
  `# TODO(api-verify)`, adjust once actual rendered colors are visible.
- **`WotstatSpotting.py`** rewritten: dropped the auto-starting Phase 1
  probe loop entirely (that was throwaway verification code, now
  superseded); added a real `F4` toggle (F2/F3 are already used by
  `wotstat-vegetation`, per `CONCEPT.md`'s own note to pick unused keys)
  wired through `InputHandler.g_instance.onKeyUp`, following
  `wotstat-vegetation`'s own confirmed-working pattern for this exact
  mechanism (`WotstatVegetation.py`'s `handleKeyUpEvent`) rather than
  guessing at the input API. While toggled on, a `BigWorld.callback(0,
  ...)`-driven loop calls `transform.computeWorldCheckpointsAndPorts()`
  + `overlay.render()` every frame.
- `core/phase1_probe.py` is now unused (nothing calls it) but left in
  place rather than deleted, in case its log-based verification is
  useful again later.
- **No restriction gate yet** (`utils/restriction.py` is still Phase
  3/empty) — the overlay currently runs in any context with a vehicle,
  same situation the Phase 1 probe was already in. Only test in
  Garage/Replay/Training Room until Phase 3 adds the gate.

Verified: `python2 -m py_compile` on both changed files, full
`./build.sh -d` packaging pass.

**CONFIRMED LIVE — `DebugDrawer` renders in this retail client.** User
tested in a Training Room (EBR 105, F4 toggle): green checkpoint cubes
and red port cubes both rendered, visible on-screen, positioned
plausibly around the hull/turret. The honest gap from earlier in this
section (only known caller was behind a disabled-by-default editor
flag) is now closed — it works in retail via direct Python calls same
as any other BigWorld module. No need for the `unit_cube_1m_proxy.model`
fallback.

One expected visual detail, not a bug: since `port['chassis']` is
defined as exactly equal to `checkpoint['top']` (confirmed formula,
section 12), their markers render at the *same world position* --
whichever color draws last wins/overlaps at that one spot. This is
correct per the engine's own definition of that port, not a rendering
mistake.

**Phase 2 core rendering is done and confirmed working end-to-end**:
data layer (`geometry.py`/`transform.py`) + rendering (`overlay.py`) +
toggle (`WotstatSpotting.py`, F4) all verified live.

---

## 18. Session 4 — visual test on EBR 105: markers near tank but "a bit too high"

First screenshot test (previous section) was on an **EBR 105** (French
8-wheeled light tank) — note this was also the *first ever visual test*
of this formula; all prior validation (sections 12-13, 16) was
numeric/log-only, on a different vehicle (`china:Ch29_Type_62C_prot`).
There is no prior "known good" visual baseline to compare against.

User's initial read (markers on distant buildings) turned out to be a
zoomed/aiming-mode camera perspective illusion, not a bug — on
re-check with a normal view, markers are confirmed near the tank, but
consistently sit **a bit higher than the actual hull/turret surface**.

Two live possibilities, not yet distinguished:
1. **Genuine per-vehicle bbox looseness**: the checkpoints come from
   `hull.hitTester.bbox`/`turret.hitTester.bbox` -- a *collision*
   envelope, not the visual mesh. The EBR 105 is unusually low/flat
   with large wheels that may be included in the hull's collision
   bbox, which could inflate `hullBboxMax.y` (and therefore the 'top'
   checkpoint, which is `max(hullBboxMax.y, turretPosOnHull.y +
   turretBboxMax.y)`) well above the visual roofline. If so, this is
   correct-per-the-engine's-own-definition, not a bug -- same category
   as the chassis/top overlap noted in section 17.
2. **A real coordinate bug**: e.g. some Y-offset being double-counted
   between `node('hull')`'s own translation and
   `chassis.hullPosition.y` being added on top of it. Not yet ruled
   out -- the formula was only ever numerically validated on one
   vehicle, and that validation checked internal consistency
   (symmetry, chassis==top, turret-port-matches-node-gun) rather than
   "does the absolute height match the visible model."

**Added temporary diagnostic logging to settle this** (remove once
resolved): `core/transform.py`'s new `getDebugSnapshot(vehicle)`
returns every raw input to the formula (both node positions,
`chassis.hullPosition`, both bboxes, `gunPosition`) rather than just
final results. `WotstatSpotting.py`'s `_overlayUpdate()` now logs a
full snapshot (raw inputs + final world checkpoints/ports) every ~90
frames, gated on `DEBUG_MODE` (already on in the user's build).

**Ask**: retest with F4, grab the `python.log`, and if possible a
screenshot from directly beside the tank (not zoomed/aiming) for the
clearest visual read. With the raw `hullBboxMax.y` /
`turretPosOnHull.y` / `turretBboxMax.y` values in hand, this should be
answerable directly rather than by further guessing.

---

## 19. Session 4 — found and fixed: a real coordinate-space bug, not a bbox/antenna quirk

User's own hypothesis ("some tanks have antennas that could influence
the box") was reasonable to check but turned out not to be the cause --
the real bug was cleaner and fully explains the observed height with
exact numbers, from the debug snapshot (EBR 105):

```
nodeHullPos         = (-369.430, 16.900, 35.493)
nodeTurretPos       = (-369.431, 17.126, 35.487)
chassisHullPosition = (0.000,   1.202,  0.000)
hullBboxMax         = (0.841,   0.262,  2.409)
turretPosOnHull     = (0.000,   0.226, -0.007)
turretBboxMax       = (0.955,   0.794,  0.987)
checkpoint[top]     = (-369.381, 19.120, 35.385)   <- what rendered
```

`turretLocalTopY = max(hullBboxMax.y, turretPosOnHull.y + turretBboxMax.y)
= max(0.262, 1.020) = 1.020`. The old formula then added
`chassisHullPosition.y` (1.202) on top of that *before* projecting
through `node('hull')`'s matrix:
`16.900 + 1.202 + 1.020 = 19.122` -- matches the logged `19.120`
(rounding) essentially exactly.

**Root cause**: `node('hull')` (the compound-model node this project
uses for the hull's world matrix -- section 10) is already the hull's
*fully-resolved* world position, with `chassis.hullPosition` baked in
by the model rig. Adding it again as a local offset before applying
that same matrix double-counts it. This is a variant of the
"Double Transformation" trap already flagged early in this file (there
about `vehicle.matrix`) -- same mistake, different mechanism (additive
offset + already-elevated matrix, instead of matrix*matrix).

The engine's own formula (section 12, `VehicleDescriptor.__initAttrs__`)
*does* add `chassis.hullPosition` -- because it computes points meant
for the vehicle ENTITY's root/ground matrix, a different matrix than
`node('hull')`. This project never used that entity-root matrix (Pattern
A / `node()` was the confirmed, validated approach from section 10), so
porting the offset along with the rest of the formula was the bug.

**Verified the fix directly against the logged numbers**
(`python3`, no game client needed -- this is exactly the "pure logic,
testable independently" split `AGENTS.md` asks for):
```
checkpoint['top'] local = (0.0, 1.02, 0.0)
-> world y = nodeHullPos.y (16.900) + 1.02 = 17.920
-> matches turretPosOnHull.y + turretBboxMax.y + nodeHullPos.y = 17.920 independently
```
17.920 is the turret's own roof height, measured completely
independently (via `node('turret')` + `turretBboxMax.y`) from the
checkpoint formula -- two different derivations landing on the same
number is strong confirmation, not a coincidence. Also reverified
`chassis port == top checkpoint` and `front`/`rear` sharing the same Y
(hull mid-height symmetry) still hold after the fix.

**Applied**: `core/geometry.py`'s `computeLocalCheckpoints()` no longer
takes or adds a `hullPos` parameter at all -- points are now purely
hull-local, matching what `node('hull')` actually expects.
`core/transform.py`'s call site updated to match (still reads
`chassis.hullPosition` for the debug snapshot, just doesn't feed it
into the formula anymore).

Verified: `python2 -m py_compile` + full `./build.sh -d` packaging
pass.

**CONFIRMED LIVE**: retested on the same EBR 105, non-zoomed side view.
Markers now sit directly on the model -- red on the turret roof, red on
the gun mantlet, green along the hull/wheels. No more floating above
the tank. User's read: "looks pretty reasonable."

**Phase 2 is now fully done and confirmed correct end-to-end**: data
layer, rendering, toggle, and this coordinate-space fix all verified
live. No known open bugs in the core checkpoint/port visualization.

---

## 20. Session 4 — polish pass: cleanup + labels + resilience

- Removed the temporary per-frame debug snapshot logging from
  `WotstatSpotting.py` (`_logDebugSnapshot`, the frame counter, the
  `DEBUG_MODE`-gated dump) now that section 19's bug is fixed and
  confirmed live -- it had served its purpose.
  `transform.getDebugSnapshot()` itself is left in place, unused but
  available, same precedent as keeping `core/phase1_probe.py` around
  after Phase 1 closed.
- `core/overlay.py`: added distinct colors per *named* port (`chassis`
  = red, `turret` = magenta) on top of the existing checkpoint/port
  color split, and added text labels via `DebugDrawer`'s `label()`
  builder (`.text(name).colour(...).position(...)`). **This is a new,
  not-yet-live-confirmed use of `DebugDrawer`** (only `cube()` has
  actually been confirmed rendering so far, section 17) -- so
  `_drawLabel()` wraps the call in try/except with a sticky
  `_labelsSupported` flag: if `label()` doesn't work the way this code
  assumes, it logs once and silently stops trying on every subsequent
  frame, rather than either crashing repeatedly or spamming the log.
  Marker boxes render either way, independent of whether labels work.
- `WotstatSpotting.py`'s `_overlayUpdate()` now wraps the vehicle
  lookup + compute + render sequence in try/except -- previously an
  unhandled exception anywhere in that chain (e.g. from the new,
  unconfirmed `label()` call) would have silently killed the
  `BigWorld.callback(0, ...)` reschedule and stopped the overlay
  updating until the next F4 toggle. Now a bad frame just logs and
  continues.

Verified: `python2 -m py_compile` + full `./build.sh -d` packaging
pass.

**CONFIRMED LIVE**: `label()` renders text correctly (readable "front",
"rear", "left", "port:turret" labels visible next to markers on an
EBR 105). This is a new confirmed API alongside `cube()`.

**User feedback**: labels didn't add much value once marker positions
were already confirmed correct, and cluttered the view -- asked for a
separate toggle rather than always-on with the overlay. Applied:
`overlay.render()` now takes a `showLabels` parameter (default
`False`), and `WotstatSpotting.py` binds a second key, **F5**, to
`g_labelsEnabled`, independent of the main **F4** overlay toggle. Text
labels off by default; marker boxes unaffected either way.

**User feedback**: switch marker shape from wireframe cubes to filled
spheres for easier at-a-glance discernment. Applied: `_drawMarker()`
now calls `.sphere().wireframe(False)` instead of
`.cube().wireframe(True)`. `sphere()` is a confirmed `DebugDrawer`
factory (section 17's binary/decompile research) but this is its first
actual live test -- if it doesn't render, `cube()` is the known-working
fallback shape to revert to.

### Next: Phase 2 rendering (`core/overlay.py`)

`transform.computeWorldCheckpointsAndPorts()` is the data source Phase
2's rendering step needs. Per this project's earlier (failed,
per-the-user Session 2/3 note) overlay attempt, the two concrete
findings already on record to apply this time: use `BigWorld.wg_draw_box`
/ `BigWorld.wg_draw_line` (Z-buffer-independent debug primitives,
confirmed to need no external model assets — see the "Rendering & API
Stability" note further up this file) rather than spawning model
instances, and watch out for the double-init/double-toggle bug (already
guarded against in `WotstatSpotting.py` via `g_probeStarted`, but a
fresh toggle-state global will need the same guard).


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

## 21. Session 5 — Phase 4 research: view range (solved) + camo % (partially solved, honest gap)

User asked to skip Phase 3 (restriction gate — still not implemented,
overlay still has zero mode gating, explicit user decision) and start
Phase 4 (derived stats). Per `AGENTS.md`'s own caution ("derived stat
formulas drift from actual game formulas after a patch — don't
hardcode assumptions"), researched whether the game already computes
combined effective values itself, rather than reimplementing the whole
equipment+crew+perk formula from scratch.

### View range — fully solved, server-authoritative, no formula needed

`circularVisionRadius` (already includes base + optics/binoculars +
crew skills + damaged-optics penalty) is pushed by the server via
`Avatar.py:1704 syncVehicleAttrs` and cached client-side. Vanilla's own
minimap view-range circle reads it directly:

`gui/Scaleform/daapi/view/battle/shared/minimap_plugins.py:496`:
```python
def _calcCircularVisionRadius(self):
    visibilityMinRadius = self._arenaVisitor.getVisibilityMinRadius()
    vehAttrs = self.sessionProvider.shared.feedback.getVehicleAttrs()
    return min(vehAttrs.get('circularVisionRadius', visibilityMinRadius), VISIBILITY.MAX_RADIUS)
```

So: `dependency.instance(IBattleSessionProvider).shared.feedback.getVehicleAttrs()['circularVisionRadius']`,
with live updates available via `feedback.onVehicleFeedbackReceived`
filtered to `FEEDBACK_EVENT_ID.VEHICLE_ATTRS_CHANGED`. Own-vehicle-only
by construction (it's *our* synced attrs). `# TODO(api-verify)`: the
exact import path `skeletons.gui.battle_session.IBattleSessionProvider`
is a well-known WoT modding interface but not yet independently
confirmed by this project's own decompile read — the *usage pattern*
(`dependency.instance(...)`) is confirmed from
`gui/battle_control/controllers/feedback_adaptor.py` and
`prebattle_setups_ctrl.py:139,232`.

### Camouflage % — partially solved, one real client-side limitation

**No live pre-computed camo value exists.** `getVehicleAttrs()` has no
camo key — confirmed by direct source inspection, camo spotting checks
are server-only.

What **is** available: the combined (base + paint/net + optional
devices + crew skill) *static* camo factors, via
`gui.shared.items_parameters.params.VehicleParams`:

```python
vehicleItem = dependency.instance(IItemsCache).items.getItemByCD(intCD)
vehicleParams = items_params.VehicleParams(vehicleItem)
vehicleParams.invisibilityStillFactor   # _Invisibility(current, atShot) namedtuple, already 0-100
vehicleParams.invisibilityMovingFactor  # same shape, for while moving
```
Confirmed usable *during battle*, not just Garage —
`prebattle_setups_ctrl.py:139,232` builds a `gui_items.Vehicle` and
calls this mid-battle. `# TODO(api-verify)`: exact field shapes
(`_Invisibility(current, atShot)`) are sourced from decompiled code
reading, not yet exercised by this project's own live test.

**Honest limitation, not fixable client-side**: bush/foliage
concealment bonus is a server-side ray/mask system with no exposed
client value. `camouflagePercent()` in this project can only ever
report base+paint/net+crew+movement/fire-state camo — the same thing
the Garage equipment-comparison screen shows — never "are you actually
hidden in this bush right now." This should be stated plainly in the
HUD/README once built, not implied to be more complete than it is.

Formula reference (`items/utils.py:227`, `items/vehicles.py:1242`) confirms
paint/net/crew are additive+multiplicative terms on a base
moving/stationary pair, terrain type is NOT a camo factor (it affects
mobility, not visibility), and firing applies a separate
`invisibilityFactorAtShot` multiplier. The public wiki's formula
(`wiki.wargaming.net/en/Battle_Mechanics` §6.6.1) is stale relative to
current code — decompiled source is authoritative here, not the wiki.

### Applied this session

`core/stats.py` (new): `getEffectiveViewRange()` (high confidence,
single pre-computed value) and `getCamouflagePercentStationary(vehicle)`
(first pass — always reports the *stationary* value regardless of
actual movement/firing state, clearly named as such; moving/at-shot
switching is a follow-up once this base pipeline is confirmed live).
Every new API call here (`dependency.instance`, `IBattleSessionProvider`,
`IItemsCache`, `VehicleParams` field shapes) is unconfirmed by this
project's own testing — much higher uncertainty than `core/transform.py`
ever had. Wired a one-shot **F6** keybind in `WotstatSpotting.py` that
logs both values on press, rather than continuous per-frame rendering,
specifically because of that uncertainty stack — verify via log first,
same pattern that worked for the checkpoint formula, before trusting
this enough to render.

**Ask**: press F6 in a Training Room, check the log for
`effective view range: ...` and `camouflage % (stationary): ...` lines
— report back whether they print real numbers, `None`, or an exception.

**Follow-up fix, same session**: the unconfirmed imports
(`dependency`, `skeletons.gui.battle_session`,
`skeletons.gui.shared.utils`, `gui.shared.items_parameters.params`)
were initially at `core/stats.py` module load time. That's a real
blast-radius risk this project hasn't taken before: if any of those
imports are wrong, `import core.stats` itself fails, which cascades up
through `WotstatSpotting.py`'s top-level `from core import stats` and
would break `init()` entirely -- taking the already-confirmed-working
F4 checkpoint overlay down with it, not just the new stats feature.
Moved every unconfirmed import inside its function, wrapped in the
existing try/except -- a stats API failure now only returns `None`
from that one function, same failure mode as everything else in this
file.

### F6 test result: `dependency` import wrong, same bug pattern as `model_assembler`

```
getEffectiveViewRange error: No module named dependency
_getVehicleItem error: No module named dependency
```

Same class of bug as section 14's `model_assembler` fix: guessed a
top-level module name, it's actually nested under a package. Research
against the `2.3.1_EU` branch specifically (not a generic/other-version
reference this time) found the real import, and cross-checked it
against this machine's own `res/packages/scripts.pkg`:

```python
from helpers import dependency          # NOT top-level `dependency`
from skeletons.gui.battle_session import IBattleSessionProvider  # this one was already correct
from skeletons.gui.shared import IItemsCache  # NOT skeletons.gui.shared.utils (that package only has `requesters`)
```

Confirmed present client-side in `scripts.pkg`:
`scripts/client/helpers/dependency.pyc`,
`scripts/client/skeletons/gui/battle_session.pyc`,
`scripts/client/skeletons/gui/shared/__init__.pyc`. No top-level
`scripts/client/dependency.pyc` exists — exactly why the guess failed.
Verbatim usage confirmed in WG's own shipped code,
`gui/battle_control/battle_ctx.py:157`:
`sessionProvider = dependency.instance(IBattleSessionProvider)`.

Also: `feedback_adaptor.py` (cited in this project's earlier research
as an `IBattleSessionProvider` usage example) turned out to have no
`dependency` import at all in this branch — a bad reference file from
the earlier research pass. Worth remembering: a class/interface being
*mentioned* in a file doesn't mean that file shows the correct import
pattern for it.

Applied: `core/stats.py` updated to the corrected import paths (still
inside the deferred, per-function try/except pattern). `intCD =
vehicle.typeDescriptor.type.compactDescr` and the exact
`VehicleParams.invisibilityStillFactor` shape remain genuinely
unconfirmed (`# TODO(api-verify)`) — next F6 test will show whether
those are also wrong, or whether view range / camo now actually
resolve.

### F6 retest: CONFIRMED WORKING, both values resolve cleanly

```
effective view range: 446
camouflage % (stationary): 21.1469995379
```

Reproduced identically on a second F6 press. No exceptions from either
function — the `helpers.dependency` / `skeletons.gui.shared`
`IItemsCache` fix (above) was the complete fix; `compactDescr` and
`invisibilityStillFactor`'s shape turned out to be correct guesses
too. Both APIs in `core/stats.py` are now live-confirmed, same
confidence level as `core/transform.py`.

**Camo number sanity check**: user's screenshot showed the vehicle
parked in/behind a bush, and expected ~50% vs. the displayed 21%. This
is very likely explained by the already-documented bush limitation
(this section, "Camouflage % — partially solved"): `21.1%` is
base+equipment+crew+stationary camo *without* bush bonus, and bush
concealment is typically a large additional multiplier applied
server-side with no client-exposed value. Not yet independently
confirmed (would need a clean in-the-open retest compared against the
Garage equipment-comparison screen's number for the same loadout), but
consistent with everything already established about this limitation
— not treated as a new bug.

### Applied: visual display

`core/overlay.py`: new `renderStats(anchorWorldPos, viewRange,
camoPercentStationary)` — draws a `View: 446m   Camo: 21% (no bush)`
style label above the vehicle (offset above `checkpoints['top']`),
reusing the same confirmed `_drawLabel()`/`DebugDrawer.label()`
mechanism from section 20. The "(no bush)" qualifier is baked into the
displayed text itself, not just code comments, so it's not misleading
in-game. Shown whenever the main overlay (F4) is on, independent of the
F5 per-marker labels toggle -- this is core information, not per-marker
debug clutter.

`WotstatSpotting.py`: stats are now computed on a throttled cache
(refreshed every 30 frames, ~0.5s at 60fps, plus immediately on the
first frame after toggling on) rather than every single frame, since
the DI/items-cache lookups in `core/stats.py` are heavier than the
checkpoint geometry math and don't need per-frame precision -- view
range and camo don't change every tick. `renderStats()` itself (a
cheap draw call) still runs every frame using the cached values, so
the label doesn't visibly lag behind the marker positions.

Verified: `python2 -m py_compile` + full `./build.sh -d` packaging
pass.

**CONFIRMED LIVE**: stats label renders correctly above the vehicle
("View: 44m   Camo: 21% (no bush)"), and view range visibly updates
with module crits — direct confirmation `getEffectiveViewRange()`
tracks live, real state, not a cached/stale value.

**Camo was actually wrong, and the bush theory was wrong too.** User
compared against the Garage "ABOUT VEHICLE" screen for the *same*
vehicle, same loadout: Concealment showed **52.87%** stationary vs.
our **21.15%** — and confirmed the number didn't change with terrain at
all (ruling out "it's just missing bush bonus," since that would still
leave the base number matching Garage's no-bush display).

### Root cause: `getItemByCD` returns a fake, unsynced item in battle

Researched with the same "check the exact decompiled source, don't
reuse a claim from a different context" discipline as the
`model_assembler`/`dependency` fixes. Confirmed in
`client/gui/shared/gui_items/vehicle.py`: `Vehicle.__init__` gates
*all* live state (crew, camo paint, consumables) behind an
inventory-sync check (`vehicle.py:304`). In battle that check fails
(no synced Garage inventory for this item), so:
- `initCrew` yields an empty crew, backfilled by
  `createFakeTankmanDescr(role, vehicleType, roleLevel=100)`
  (`items_parameters/functions.py:219,225`) — **100% qualification,
  zero trained skills, no perks** (no Camouflage skill, no BiA).
- `_outfitComponents` stays empty → `getBonusCamo()` returns `None` →
  **no camo paint bonus**.
- `_invData` stays empty → **no consumables/food/boosters**.

That combination — real vehicle, fake empty-skill crew, no paint, no
food — is exactly the gap between 52.87% (real) and 21.15% (what a
"clean" crew with just base equipment would show). `VehicleParams`
itself is fully capable of factoring all of this in — the bug was
never in the formula, it was in what item we fed it.

### Fix: read directly from the live vehicle entity, not a Garage item lookup

Same category of fix as trusting `vehicle.typeDescriptor` over any
Garage-inventory API for the checkpoint geometry. Confirmed the live
vehicle entity replicates real data for the player's own vehicle:
`entity_defs/vehicle.def:144` — `crewCompactDescrs`, `DetailLevel
MY_VEHICLE` (i.e. only sent for your own vehicle, consistent with the
project's own-vehicle-only architecture). Camo comes from
`vehicle.publicInfo.outfit`.

```python
vehicleDescr = vehicle.typeDescriptor
crewCompactDescrs = list(vehicle.crewCompactDescrs)  # real skills/perks

sessionProvider = dependency.instance(IBattleSessionProvider)
eqs = [item.getDescriptor() for item in sessionProvider.shared.equipments.getEquipments().values() if item is not None]

factors = vehicleAttributeFactors()
items_utils.updateAttrFactorsWithSplit(vehicleDescr, crewCompactDescrs, eqs, factors)

camouflageId = None
outfitComponent = camouflages.getOutfitComponent(vehicle.publicInfo.outfit, vehicleDescr)
for camo in outfitComponent.camouflages:
  if camo.appliedTo & ApplyArea.HULL:
    camouflageId = camo.id
    break

baseInvisibility = vehicleDescr.computeBaseInvisibility(factors['camouflage'], camouflageId)
factors['invisibility'] = factors['invisibility'][VEHICLE_TTC_ASPECTS.WHEN_STILL]
stillPercent = items_utils.getInvisibility(vehicleDescr, factors, baseInvisibility, False) * 100.0
```

`items_utils.updateAttrFactorsWithSplit` is the confirmed "assembler"
function — same one `VehicleParams` itself calls internally
(`params.py:1076-1081`), just fed real crew/equipment data instead of
the fake item's empty data. `computeBaseInvisibility` returns a
`(moving, still)` tuple; `getInvisibility(..., isMoving=False)` selects
index 1. This is `getVehicleFactors`'s Garage-default behavior
(`isModifySkillProcessors=False`), matching the 52.87% figure rather
than the in-battle-recalculated variant.

**Bush limitation is unchanged** — this formula still has no terrain
awareness (same underlying `getInvisibility` function, no map/position
input at all), so the "(no bush)" label stays accurate and necessary.

Applied to `core/stats.py`: `_getVehicleItem`/`VehicleParams`/
`IItemsCache` path removed entirely, replaced with the above. Every API
in this new path is sourced with file:line citations from the
`2.3.1_EU` decompile but **not yet exercised by this project's own live
test** — next F6/visual check will confirm whether it actually resolves
to something near 52.87%, or surfaces a next wrong guess (e.g.
`sessionProvider.shared.equipments` or `camouflages.getOutfitComponent`
signatures).

Verified: `python2 -m py_compile` + full `./build.sh -d` packaging
pass.

**CONFIRMED LIVE, real progress but not exact yet**: computed 44%,
Garage shows 52.87% for the same vehicle/loadout, no errors logged. Up
from 21% before this fix, but ~9 points still unexplained. Ruled out
bush again (this test happened while parked in a bush; the "(no bush)"
value should be terrain-independent either way, and both numbers are
meant to be the no-bush baseline).

### Follow-up research: two leads, one ruled out, one uncertain

- **`additionalCrewLevelIncrease` (food skill-boost argument) — ruled
  out.** Confirmed: it's `0.0` unless a `situationalBonuses` list is
  explicitly passed, which only happens in crew-comparison *tooltips*,
  never in normal stat display. The Garage's own 52.87% figure is
  computed the same way this project's code already does (omitting
  it). Not the gap.
- **Food/consumables reach the crew through the equipment descriptor
  itself** (`eq.crewLevelIncrease` summed in `updateVehicleAttrFactors`),
  not a separate argument — so as long as the right items are in `eqs`,
  food is already covered by the existing code shape.
- **Confirmed: optional devices (camo net etc.) are already baked into
  `vehicleDescr` and must NOT be added to `eqs`** — doing so would
  double-count them. Good, this project's code doesn't add them.
- **Uncertain (medium confidence): `sessionProvider.shared.equipments`
  may only return "regular" battle consumables (repair kit, med kit,
  food) and structurally exclude `battleBoosters` (crew-skill
  directives)** — those can meaningfully move camo and aren't reachable
  from any battle-side controller this research found. This is the
  leading theory for the remaining ~9 points, but not proven.
- The research's own suggested fix (route back through
  `IItemsCache.items.getItemByCD(...)` + `getVehicleFactors(guiVeh)` to
  pick up boosters) was **not applied** — it risks reintroducing the
  exact unsynced-item/fake-crew problem this session already diagnosed
  and fixed above. Applying it without checking would be trading a
  known-fixed bug for a maybe-fixed one.

**Chose diagnosis over another guess.** Added
`stats.getCamouflageDebugSnapshot(vehicle)` (diagnostic-only, mirrors
`transform.getDebugSnapshot`) exposing `factors['crewLevelIncrease']`,
`factors['camouflage']`, the raw `factors['invisibility']` tuple, the
names of items actually in `eqs`, and
`vehicleDescr.optionalDevices` names. Wired into F6's log output,
right after the existing view-range/camo lines. This directly answers
whether food/consumables are actually present in `eqs` (if food is
missing, that's the gap; if it's present with a sane
`crewLevelIncrease` and the gap persists, the booster theory gets more
likely) — real numbers instead of a fourth speculative rewrite.

Verified: `python2 -m py_compile` + full `./build.sh -d` packaging
pass. **Not yet verified live.**

**Status check-in point**: this is the third research/fix round on
camouflage specifically. 44% (mechanically correct pipeline, honest
"(no bush)" label, food/net not double-counted) may be an acceptable
place to stop chasing exactness, depending on how much precision this
project actually needs here — worth an explicit decision with the user
rather than continuing to iterate indefinitely, especially if the next
debug snapshot doesn't cleanly point to a fix.

### F6 debug-snapshot result: pinpointed the exact missing device

User did excellent diagnostic work independently: compared the Garage
"Configuration" screen with Low Noise Exhaust System equipped
(52.87%) vs. removed (43.87%) — matching this project's computed 44%
almost exactly to the "without" case. `eqNames = ['smallMedkit',
'hotCoffee', 'smallRepairkit']` (no Low Noise Exhaust) and
`optionalDeviceNames = []` (empty) confirmed neither data source this
project was reading captured the device at all.

### Fourth research round: root cause found, with exact arithmetic proof

`additionalInvisibilityDevice` (Low Noise Exhaust System's internal
name) is `ITEM_TYPES.optionalDevice` — a different item type than
`ITEM_TYPES.equipment` (consumables), which is exactly why
`shared.equipments.getEquipments()` never had it; that controller only
serves the consumables type. Its bonus is applied via
`LowNoiseTracks.updateVehicleDescrAttrs()`
(`items/artefacts.py:509`) directly into
`vehicleDescr.miscAttrs['invisibilityAdditiveTerm']` — not into
`factors`, so `applyOptDevFactorsForAspect` alone would never surface
it either.

**Verified by exact arithmetic against both observed numbers** — EBR
105's base still-invisibility is `0.371`
(`item_defs/vehicles/france/F108_Panhard_EBR_105.xml:18`), and the
device's `invisibilityBonus` is `0.06`/`0.08` (regular/improved slot):
```
without: (0.371 + 0.019) * 1.125 = 0.43875 -> 43.87%  <- matches Garage exactly
with:    (0.371 + 0.019 + 0.08) * 1.125 = 0.52875 -> 52.87%  <- matches Garage exactly
```
Not a plausible guess — an exact match to two independently-observed
numbers from two different UI screens.

`vehicleDescr.miscAttrs['invisibilityAdditiveTerm']` **is** already
read by `items_utils.getInvisibility()` — the function this project's
code already calls. So the bug wasn't a missing formula term, it was
either (a) this project's manually-reconstructed call sequence somehow
not benefiting from a value that should already be there, or (b) our
`vehicleDescr`/`optionalDevices` genuinely not reflecting the fitted
device for a reason the research couldn't fully pin down from source
alone.

**Fix applied**: switched from manually reassembling
`computeBaseInvisibility()` + `getInvisibility()` + hand-picking the
`WHEN_STILL` aspect, to the game's own purpose-built client function,
`items.utils.getClientInvisibility(vehicleDescr, vehicle, camouflageFactor, factors)`
— takes the live vehicle entity directly and returns `(moving, still)`.
This is a cleaner, more "designed for this exact use case" API than
hand-rolling the same formula, and sidesteps whatever specific mistake
was in the manual version.

`core/stats.py`'s `getCamouflageDebugSnapshot()` also now exposes
`invisibilityAdditiveTerm`/`invisibilityBaseAdditive` directly from
`vehicleDescr.miscAttrs`, so the next test will show directly whether
the `0.08` device bonus is actually present on our `vehicleDescr` —
settling (a) vs (b) above with one more log line regardless of whether
`getClientInvisibility` alone fixes it.

Verified: `python2 -m py_compile` + full `./build.sh -d` packaging
pass.

### F6 retest: getClientInvisibility dead end, but confirms the real cause

```
getCamouflagePercentStationary error: Type : Vehicle has no attribute: getBonusCamo
...
invisibilityAdditiveTerm = 0.0
invisibilityBaseAdditive = 0.0
```

`getClientInvisibility(vehicleDescr, vehicle, ...)` internally calls
`vehicle.getBonusCamo()` — a method that only exists on the
Garage-style `gui_items.Vehicle` wrapper, not the raw battle entity.
"Takes the live vehicle directly" (fourth research round's own
description) was imprecise — it needs the *wrapper*, and this project
already confirmed that wrapper is fake/unsynced in battle (the very
first camo fix, earlier in this section). Dead end, reverted.

**The debug snapshot settles the open question from the fix above**:
`invisibilityAdditiveTerm`/`invisibilityBaseAdditive` are both
genuinely `0.0` on the live `vehicleDescr`, confirming case (b) from
the third fix's own notes — this project's `vehicleDescr` (from
`vehicle.typeDescriptor` on the battle entity) simply does not reflect
the fitted Low Noise Exhaust System device, for a reason four research
rounds couldn't determine from source alone. Not a formula bug on this
project's side; a genuine input-data gap.

**Decision: stop chasing this specific device, document it as a second
known limitation.** Reverted `getCamouflagePercentStationary()` to the
manual `computeBaseInvisibility()`/`getInvisibility()` sequence (the
"third fix" version, minus `getClientInvisibility`) — this is the
correct, working formula given the data this project can actually
access; it was never wrong, the *input* was incomplete. Updated
`core/stats.py`'s module docstring and `core/overlay.py`'s on-screen
label to be honest about this: camo is now framed as a **lower bound**
("45%+ (min)" style, not "45% (no bush)") rather than implying
precision the underlying data can't support. Two documented gaps now,
same category as each other: bush bonus (never obtainable) and *some*
optional devices' bonuses (obtainable in principle, but this project's
current data source doesn't have them for at least this one confirmed
case).

Verified: `python2 -m py_compile` + full `./build.sh -d` packaging
pass. **Not yet verified live** for the reverted formula + new label
text (though the formula itself was already confirmed working at 44%
before the `getClientInvisibility` detour, so this is mostly a
text/framing change plus removing the broken call).

---

## 22. Session 5 — vegetation-merge feasibility check, then Phase 4 removed entirely

User asked whether `wotstat-vegetation` could be merged in to compute
the actual bush-bonus camo value (rather than just labeling the gap).
Researched properly rather than assuming it was the same dead end as
the earlier bush finding:

- The vegetation density data itself is real, shipped game data (398
  vegetation objects in this client's `destructibles.xml`, densities
  of exactly `0.25`/`0.5`, matching `wotstat-vegetation`'s own
  classification) — not a heuristic table. `wotstat-vegetation`
  already solves reading it.
- But the mechanic is **structurally per-enemy**: it's a ray/
  line-of-sight test computed independently for each enemy's viewpoint
  against your checkpoints, not a property of your own tank alone. The
  server attribute (`foliageInvisibilityFactor`) is flagged
  `CELL_PRIVATE` in the game's own entity definition — never sent to
  any client, ever. The combining formula also isn't in the shared
  client+server code, only server-side.
- Conclusion: an accurate bush bonus **cannot** be computed from own
  data alone — it inherently requires the enemy's position, which is
  exactly the category this project's non-goals already rule out (no
  enemy-relative prediction, no data about specific opponents). Not
  pursued, for the same reason the project's hard scope wall exists,
  not just a technical limitation.
- Noted a legitimately in-scope alternative if ever wanted later: a
  directional "dense/sparse foliage cover toward direction X" hint
  using only own-checkpoint raycasts against local vegetation data —
  a positioning aid, not a camo percentage, no enemy data needed. Not
  built; just recorded as a real option for the future.

**Decision: remove Phase 4 (view range + camo) entirely, keep only
Phase 2 (checkpoints/ports).** After four research rounds on camo
alone hit a genuine, well-confirmed dead end (device-bonus gap
unexplained even at the source level; bush bonus structurally
unobtainable without crossing the project's own non-goals), the user
chose to drop the feature rather than ship a permanently-caveated
"45%+ (min)" number.

Removed: `core/stats.py` (deleted entirely, not just gutted —
`getEffectiveViewRange()`, `getCamouflagePercentStationary()`,
`getCamouflageDebugSnapshot()`, all their now-confirmed and
now-abandoned API paths). `core/overlay.py`'s `renderStats()` and its
label constants removed. `WotstatSpotting.py`: removed the `stats`
import, the stats cache/frame-counter globals, `_refreshStatsCache()`,
`_logStatsSnapshot()`, the F6 keybind entirely, and the
`overlay.renderStats(...)` call from the per-frame loop. F4 (overlay
toggle) and F5 (label toggle) are unchanged.

Verified: `python2 -m py_compile` on both changed files, `grep` confirms
zero remaining references to `stats`/`core.stats` anywhere in `res/`,
and a full `./build.sh -d` packaging pass — package size dropped from
~24KB to ~14KB, consistent with a clean removal rather than dead code
left behind.

**Current scope, for anyone picking this project up**: Phase 0-2 done
and confirmed live (scaffolding, research, own-vehicle
checkpoint/port visualization with F4 toggle + F5 optional labels).
Phase 3 (restriction gate) skipped by explicit user decision — still
no game-mode gating, only test in Garage/Replay/Training Room. Phase 4
(derived stats) built, partially fixed across multiple rounds, then
removed by explicit user decision after hitting real, well-documented
technical limits. Phase 5/6 (polish, release) not started.

---

## 23. Session 5 — angle-based exposure hints (the one Phase 4 idea that survived)

After the camo/view-range removal, recommended this as the one
remaining Phase 4-era idea worth building: unlike camo, it needs zero
new game-API lookups -- it's pure vector math on data
`core/transform.py` already computes and has had confirmed live for
sessions. `CONCEPT.md` section 3 explicitly scoped this as legitimate
from the start: "visualize checkpoint exposure relative to hull/turret
facing and camera direction, **not** relative to any actual enemy
position."

**Design**: classify each of the 6 checkpoints by the angle between
its own hull-local (x, z) offset and hull-forward (the fixed local
`(0, 0, 1)` axis in the same frame `core/geometry.py`'s
`computeLocalCheckpoints` already uses -- confirmed by the fact
`front`/`rear` checkpoints are literally defined by `hullBboxMax.z`/
`hullBboxMin.z`). Bucketed via `cos(45deg)` thresholds into
`'facing'`/`'side'`/`'rear'`. Y (height) is ignored -- this is about
horizontal facing, not vertical position. A checkpoint sitting exactly
on the centerline (`'top'`, local x=z=0) has no defined direction and
defaults to `'facing'`.

Sanity-tested independently with `python3` (no game client) against
both `computeLocalCheckpoints`' actual output and synthetic 30/60-degree
offsets -- `front`/`gunMount`/`top` all classify `'facing'`,
`'rear'` classifies `'rear'`, `'left'`/`'right'` classify `'side'`,
30deg-from-forward is `'facing'`, 60deg is `'side'`. All passed.

**Architecture note**: initially implemented in `core/geometry.py`
directly, then moved to a new `core/exposure.py` -- `CONCEPT.md`
section 5's original architecture sketch scaffolded a *dedicated*
`core/exposure.py` module for exactly this ("angle-based exposure
heuristics"), separate from `geometry.py`'s checkpoint/port offset
math, and that file had sat empty since Phase 0. Moved
`classifyExposure`/`EXPOSURE_BUCKETS` there and added
`classifyAllExposures(localCheckpoints)` as the dict-batch entry point
`core/transform.py` calls, keeping the same
zero-game-API-imports/independently-testable split as `geometry.py`.

**Wired through the existing pipeline, no new visualization layer**
(matches `TASKS.md`'s own plan: "tint 'facing' checkpoints
differently... rather than adding a whole separate visualization"):
- `transform.computeWorldCheckpointsAndPorts()` now returns a 3-tuple,
  `(checkpoints, ports, exposures)` -- a breaking change to its return
  arity, updated at its one call site in `WotstatSpotting.py`.
- `overlay.render()` gained an `exposures=None` parameter; when given,
  it tints each checkpoint marker by bucket instead of the old flat
  green. Colors picked to avoid clashing with the existing port colors
  (red=chassis, magenta=turret): `facing`=orange, `side`=yellow,
  `rear`=green (same as the old flat default, so a stationary
  head-on view looks unchanged from before this feature).
- No new keybind -- exposure coloring is always on whenever the F4
  overlay is on; F5 labels still work identically (checkpoint names),
  independent of the new colors.

**Cleanup while touching this code**: deleted `core/phase1_probe.py`
(verification wrapper for the Phase1->Phase2 migration, unused since
that migration was long since confirmed -- `AGENTS.md` itself says to
delete it once Phase 1 is fully confirmed, and it would have broken
outright on the new 3-tuple return anyway since nothing was maintaining
it).

Verified: `python2 -m py_compile` on all five touched/added files,
`grep` confirms no leftover references to the deleted file, and a full
`./build.sh -d` packaging pass. **Not yet verified live** -- next test
is F4 in Training Room, rotating the hull, and checking that
front-ish checkpoints go orange, side checkpoints yellow, and
rear-ish checkpoints stay green as the tank turns.

---

## 24. Session 5 — per-step diagnostic logging, so a future WoT patch is traceable

User asked: since this project has accumulated a long list of
`# TODO(api-verify)` assumptions across `core/transform.py` and
`core/overlay.py` (compoundModel node names, `hitTester.bbox` shape,
`Matrix.applyPoint`, `DebugDrawer` builder methods...), how would a
future WoT patch that breaks one of them actually show up in the log,
in a way that's traceable back to the specific broken assumption
rather than one vague bundled exception?

**Before this session**: `computeWorldCheckpointsAndPorts()` had ONE
try/except around its entire body -- any failure inside collapsed into
a single generic `"computeWorldCheckpointsAndPorts error: <exception>"`
message with no indication of which of its ~6 internal steps broke.
`overlay.py`'s `_drawMarker()` (the sphere-drawing call, i.e. the core
visible feature) had **zero** error handling at all -- a break there
would propagate up to `WotstatSpotting.py`'s outer catch and log an
even more generic `"overlay update error: ..."`, and would do so
**every single frame** (60x/second) for as long as the overlay stayed
on, since nothing there was sticky/one-time.

**Applied**: broke `computeWorldCheckpointsAndPorts()` into 6
individually-wrapped steps (`typeDescriptor` read, `hitTester.bbox`
read, node-matrix lookup, typeDescriptor sub-field reads, the pure-math
`geometry.computeLocalCheckpoints` call, and the final
`Matrix.applyPoint` projection), each logging a specific `"BROKEN: ..."`
message naming the exact API call(s) involved and pointing at the
relevant `NOTES.md` section for context -- but only **once per
session** (a `_diagnosticsLogged` dict + `_logOnce()` helper), so a
persistent break logs one clear line instead of spamming. Same
treatment for `findOwnVehicle()`. `overlay.py`'s `_drawMarker()` got
the same sticky-once try/except `_drawLabel()` already had (that
existing pattern was the template for all of this). `WotstatSpotting.py`'s
outer catch-all is now also sticky, explicitly labeled as a
last-resort ("not caught more specifically in transform.py/overlay.py")
so its presence in a log signals something genuinely new/unanticipated
rather than one of the already-named failure modes.

Net effect: if a future WoT patch breaks, say, `compoundModel.node()`,
the log will show exactly one line: `"BROKEN:
vehicle.appearance.compoundModel.node()/Math.Matrix() (NOTES.md
section 10) -- <real exception text>"`, immediately after toggling F4,
and nothing else repeating every frame. That's directly actionable —
compare against `NOTES.md` section 10's confirmed API history to see
what changed, without needing to bisect which of the ~15 assumptions
in this project broke by trial and error.

Verified: `python2 -m py_compile` on all three touched files, full
`./build.sh -d` packaging pass. This doesn't change any working
behavior (every currently-confirmed API path is unaffected) -- it's
purely additive diagnostic infrastructure, so no live retest is
strictly required, though the next normal F4 test will exercise it
implicitly (no `BROKEN:` lines should appear if everything's still
working as of `2.3.1_EU`).
