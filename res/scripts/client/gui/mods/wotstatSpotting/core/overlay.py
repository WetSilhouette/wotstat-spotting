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

_CHECKPOINT_COLOR = 0xFF00FF00  # green -- confirmed rendering correctly
_PORT_COLORS = {
  'chassis': 0xFFFF3030,  # red -- static, hull-relative (== checkpoint['top'])
  'turret': 0xFFFF00FF,  # magenta -- the one point that tracks turret rotation live
}
_CHECKPOINT_SIZE = 0.15  # meters, cube edge length
_PORT_SIZE = 0.22
_STATS_LABEL_COLOR = 0xFFFFFFFF  # white
_STATS_LABEL_HEIGHT_OFFSET = 0.6  # meters above the anchor point, so it doesn't overlap the top checkpoint marker

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


def render(checkpoints, ports, showLabels=False):
  """
  Draws one frame's worth of markers from
  core.transform.computeWorldCheckpointsAndPorts()'s output. Must be
  called every frame while the overlay is toggled on -- see the module
  docstring on why nothing persists between calls. showLabels is a
  separate toggle from the overlay itself (see WotstatSpotting.py) --
  text labels didn't add much once the marker positions were already
  confirmed correct, so they default off.
  """
  for name, worldPos in checkpoints.items():
    _drawMarker(worldPos, _CHECKPOINT_SIZE, _CHECKPOINT_COLOR)
    if showLabels:
      _drawLabel(worldPos, name, _CHECKPOINT_COLOR)
  for name, worldPos in ports.items():
    color = _PORT_COLORS.get(name, _CHECKPOINT_COLOR)
    _drawMarker(worldPos, _PORT_SIZE, color)
    if showLabels:
      _drawLabel(worldPos, 'port:' + name, color)


def renderStats(anchorWorldPos, viewRange, camoPercentStationary):
  """
  Draws a floating text label near the vehicle showing effective view
  range and stationary camouflage %. anchorWorldPos is typically
  checkpoints['top'] -- the label is offset above it so it doesn't
  overlap that marker. Shown whenever the overlay is on, independent of
  showLabels (this is core information, not per-marker debug clutter).

  Camo is explicitly labeled "(min)" -- see core/stats.py's module
  docstring and NOTES.md section 21: this can only ever be a same-or-
  lower estimate of the vehicle's true camo (missing bush/foliage
  bonus always, and some optional devices' bonuses depending on the
  device), never an exact or over-stated figure.
  """
  viewRangeText = ('%.0fm' % viewRange) if viewRange is not None else '?'
  camoText = ('%.0f%%+ (min)' % camoPercentStationary) if camoPercentStationary is not None else '?'
  text = 'View: %s   Camo: %s' % (viewRangeText, camoText)
  labelPos = Math.Vector3(anchorWorldPos[0], anchorWorldPos[1] + _STATS_LABEL_HEIGHT_OFFSET, anchorWorldPos[2])
  _drawLabel(labelPos, text, _STATS_LABEL_COLOR)
