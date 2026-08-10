# -*- coding: utf-8 -*-
# Pure-Python geometry math -- NO game-API imports (BigWorld/Math/etc.),
# see AGENTS.md: "keep local checks ... in files with no game-API
# imports so it's testable in isolation." core/transform.py supplies
# the game-API glue and converts to/from the engine's own Vector3 type.
#
# Points in and out of this module are plain (x, y, z)-indexable values
# (a tuple, or anything supporting [0]/[1]/[2], including the engine's
# own Vector3 -- callers can pass either).
#
# Formula ported from the live game engine's own
# VehicleDescriptor.__initAttrs__ (server/editor-only code, confirmed by
# decompiling this project's own client -- see NOTES.md section 12) and
# validated against a live vehicle across multiple sessions (NOTES.md
# sections 13, 19): 5 of the 6 checkpoints, plus the 'chassis' port, are
# rigidly hull-relative and use a *static, neutral-pose* gun offset --
# they never track live turret rotation. Only the 'turret' port
# (== gunPosition, projected via the turret's own world matrix in
# core/transform.py) tracks turret rotation live.
#
# NOTES.md section 19: unlike the engine's own formula, this version
# does NOT add chassis.hullPosition to these points. The engine formula
# computes points relative to the vehicle ENTITY's root/ground origin,
# for use with the vehicle's own world matrix. This project instead
# projects through core/transform.py's node('hull') matrix, which is
# already the hull's fully-resolved world frame (hullPosition baked in
# by the model rig) -- adding it again here double-counted that offset
# and floated every marker up by chassis.hullPosition.y (confirmed live
# on an EBR 105: ~1.2m too high, exactly matching that vehicle's
# hullPosition.y).

CHECKPOINT_NAMES = ('top', 'gunMount', 'front', 'rear', 'right', 'left')
PORT_NAMES = ('chassis', 'turret')


def _add(a, b):
  return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def computeLocalCheckpoints(hullBboxMin, hullBboxMax, turretPosOnHull, turretBboxMax, gunPosition):
  """
  All arguments are points local to the HULL's own coordinate frame --
  i.e. the same frame as core/transform.py's node('hull') matrix, NOT
  the vehicle entity's root/ground position (see the module docstring).
  Returns (checkpoints, observerOnChassis):
  - checkpoints: dict of CHECKPOINT_NAMES -> local (x, y, z), meant to
    be projected into world space via the HULL's world matrix.
  - observerOnChassis: a single local (x, y, z), also hull-matrix-
    projected -- this is the 'chassis' view range port.
  The 'turret' port is deliberately not computed here: it is simply
  gunPosition itself, projected via the TURRET's world matrix instead
  (the one point that tracks live turret rotation).
  """
  gunPosOnHull = _add(turretPosOnHull, gunPosition)
  turretLocalTopY = max(hullBboxMax[1], turretPosOnHull[1] + turretBboxMax[1])
  hullLocalCenterY = (hullBboxMin[1] + hullBboxMax[1]) / 2.0
  hullLocalCenterZ = (hullBboxMin[2] + hullBboxMax[2]) / 2.0

  top = (0.0, turretLocalTopY, 0.0)
  checkpoints = {
    'top': top,
    'gunMount': gunPosOnHull,
    'front': (0.0, hullLocalCenterY, hullBboxMax[2]),
    'rear': (0.0, hullLocalCenterY, hullBboxMin[2]),
    'right': (hullBboxMax[0], gunPosOnHull[1], hullLocalCenterZ),
    'left': (hullBboxMin[0], gunPosOnHull[1], hullLocalCenterZ),
  }
  observerOnChassis = top
  return checkpoints, observerOnChassis
