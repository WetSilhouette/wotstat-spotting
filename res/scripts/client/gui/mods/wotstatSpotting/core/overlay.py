# -*- coding: utf-8 -*-
# Renders the 6 checkpoints + 2 view range ports as world-space markers
# using BigWorld's native DebugDrawer module -- compiled into the
# client, no custom .model/.visual assets needed.
#
# CONFIRMED LIVE (NOTES.md section 17, fix verified in section 19):
# cube()/colour()/position()/scale() all render correctly in this
# retail client. Text labels (below, via label()) are also now
# confirmed live (NOTES.md section 20) -- the try/except fallback stays
# as a safety net, not because it's still expected to fire. Markers
# switched from wireframe cubes to filled (wireframe(False)) spheres
# for easier at-a-glance discernment -- sphere() is a confirmed
# DebugDrawer factory (section 17's research) but not yet itself
# live-tested; if it doesn't render, cube() is the known-working
# fallback shape.
#
# DebugDrawer calls are immediate-mode -- nothing persists between
# frames, matching WG's own tick()-based caller. render() must be
# called every frame while the overlay is toggled on (see
# WotstatSpotting.py, which also wraps this call in a try/except so a
# rendering hiccup can't kill the per-frame reschedule loop).
import DebugDrawer
import Math

from ..utils.logger import log

_CHECKPOINT_COLOR = 0xFF00FF00  # green -- confirmed rendering correctly, fallback if exposure unavailable
# Angle-based exposure hints (core/geometry.py:classifyExposure) --
# purely self-referential to the vehicle's own hull orientation, never
# enemy data (CONCEPT.md section 3). Colors chosen to avoid clashing
# with the port colors below (no red, no magenta): green/yellow/orange
# reads as a "how toward-your-own-facing-direction is this point"
# gradient, not a safety claim.
_EXPOSURE_COLORS = {
  'facing': 0xFFFF8800,  # orange
  'side': 0xFFFFFF00,  # yellow
  'rear': 0xFF00FF00,  # green -- same as the old flat checkpoint color
}
_PORT_COLORS = {
  'chassis': 0xFFFF3030,  # red -- static, hull-relative (== checkpoint['top'])
  'turret': 0xFFFF00FF,  # magenta -- the one point that tracks turret rotation live
}
_CHECKPOINT_SIZE = 0.15  # meters, cube edge length
_PORT_SIZE = 0.22

# Sticky flag: if label() turns out not to exist/behave as expected,
# stop trying after the first failure instead of throwing every frame.
_labelsSupported = True


def _drawMarker(worldPos, size, color):
  (DebugDrawer.DebugDrawer()
    .sphere()
    .zTest(False)
    .wireframe(False)
    .colour(color)
    .position(worldPos)
    .scale(Math.Vector3(size, size, size)))


def _drawLabel(worldPos, text, color):
  global _labelsSupported
  if not _labelsSupported:
    return
  try:
    (DebugDrawer.DebugDrawer()
      .label()
      .text(text)
      .colour(color)
      .position(worldPos))
  except Exception as e:
    _labelsSupported = False
    log('DebugDrawer label() not supported, disabling text labels: ' + str(e))


def render(checkpoints, ports, exposures=None, showLabels=False):
  """
  Draws one frame's worth of markers from
  core.transform.computeWorldCheckpointsAndPorts()'s output. Must be
  called every frame while the overlay is toggled on -- see the module
  docstring on why nothing persists between calls. showLabels is a
  separate toggle from the overlay itself (see WotstatSpotting.py) --
  text labels didn't add much once the marker positions were already
  confirmed correct, so they default off.

  exposures, if given, is a dict of checkpoint name -> one of
  geometry.EXPOSURE_BUCKETS ('facing'/'side'/'rear'), used to tint each
  checkpoint marker instead of the flat default color -- see
  core/geometry.py:classifyExposure. None (the default) falls back to
  the flat green for every checkpoint, e.g. if the caller doesn't have
  exposure data for some reason.
  """
  for name, worldPos in checkpoints.items():
    bucket = exposures.get(name) if exposures else None
    color = _EXPOSURE_COLORS.get(bucket, _CHECKPOINT_COLOR)
    _drawMarker(worldPos, _CHECKPOINT_SIZE, color)
    if showLabels:
      _drawLabel(worldPos, name, color)
  for name, worldPos in ports.items():
    color = _PORT_COLORS.get(name, _CHECKPOINT_COLOR)
    _drawMarker(worldPos, _PORT_SIZE, color)
    if showLabels:
      _drawLabel(worldPos, 'port:' + name, color)
