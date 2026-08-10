# -*- coding: utf-8 -*-
# Angle-based exposure hints -- pure Python, NO game-API imports, same
# testable-in-isolation split as core/geometry.py (AGENTS.md). Purely
# self-referential to the vehicle's own hull orientation, NEVER enemy
# data (CONCEPT.md section 3: "visualize checkpoint exposure relative
# to hull/turret facing and camera direction, not relative to any
# actual enemy position" -- explicitly the one Phase 4 idea that
# doesn't share the camo/view-range removal's problems, since it needs
# no new game-API lookups at all, only data core/transform.py already
# has confirmed live: the checkpoints' own hull-local offsets).

EXPOSURE_BUCKETS = ('facing', 'side', 'rear')

# cos(45deg) -- a checkpoint within 45 degrees of hull-forward is
# 'facing', within 45 of hull-rearward is 'rear', otherwise 'side'.
_FACING_COS_THRESHOLD = 0.7071067811865476


def classifyExposure(localCheckpointOffset):
  """
  Classifies a single checkpoint's exposure bucket purely from its own
  local (x, y, z) offset relative to the hull center -- never relative
  to any enemy position. Hull-forward is the fixed local +Z axis in
  this frame (the same convention core/geometry.py's 'front'/'rear'
  checkpoints already use -- see NOTES.md section 12).

  Ignores the Y (height) component -- exposure is about horizontal
  facing, not vertical position. A checkpoint sitting exactly on the
  hull's centerline (e.g. 'top', local x=z=0) has no defined horizontal
  direction and defaults to 'facing'.
  """
  x, z = localCheckpointOffset[0], localCheckpointOffset[2]
  magnitude = (x * x + z * z) ** 0.5
  if magnitude < 1e-6:
    return 'facing'
  cosAngleFromForward = z / magnitude
  if cosAngleFromForward >= _FACING_COS_THRESHOLD:
    return 'facing'
  if cosAngleFromForward <= -_FACING_COS_THRESHOLD:
    return 'rear'
  return 'side'


def classifyAllExposures(localCheckpoints):
  """
  localCheckpoints: dict of geometry.CHECKPOINT_NAMES -> local (x, y, z)
  (the first return value of geometry.computeLocalCheckpoints(), before
  world-space projection). Returns a same-keyed dict of exposure
  buckets.
  """
  exposures = {}
  for name, offset in localCheckpoints.items():
    exposures[name] = classifyExposure(offset)
  return exposures
