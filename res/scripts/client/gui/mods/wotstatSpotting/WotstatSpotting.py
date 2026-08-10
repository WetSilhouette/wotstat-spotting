# -*- coding: utf-8 -*-
from utils.logger import log
import BigWorld
import Keys
from gui import InputHandler

from core import transform
from core import overlay
from core import stats

VERSION = '{{VERSION}}'
DEBUG_MODE = '{{DEBUG_MODE}}'

# Guards against the double-init bug documented in NOTES.md section 8:
# the game can load this module twice (once from .py, once from the
# compiled .pyc), which without this guard would register the keybind
# handler twice (double-toggling on a single keypress).
if 'g_initDone' not in globals():
  g_initDone = False

if 'g_overlayEnabled' not in globals():
  g_overlayEnabled = False

if 'g_labelsEnabled' not in globals():
  g_labelsEnabled = False

if 'g_statsCache' not in globals():
  g_statsCache = {'viewRange': None, 'camo': None}

if 'g_statsFrameCounter' not in globals():
  g_statsFrameCounter = 0

# Stats involve dependency-injection/items-cache lookups (see
# core/stats.py, NOTES.md section 21) that are heavier than the
# checkpoint geometry math and don't need per-frame precision (view
# range/camo don't change every tick) -- refresh every N frames instead
# of every one, and render the cached value in between.
_STATS_REFRESH_EVERY_N_FRAMES = 30  # ~0.5s at 60fps

# F2/F3 are already used by wotstat-vegetation's own toggle keys (see
# CONCEPT.md: "pick unused keys to avoid conflicts if both mods are
# installed together").
_TOGGLE_KEY = Keys.KEY_F4
_LABELS_TOGGLE_KEY = Keys.KEY_F5
# One-shot diagnostic, not a toggle -- see NOTES.md section 21. Phase 4's
# stats APIs are unconfirmed by live testing; logging on demand is lower
# risk than wiring them into the per-frame render loop before that.
_STATS_LOG_KEY = Keys.KEY_F6

# NOTE: no restriction-gate check yet (utils/restriction.py is Phase 3,
# still empty) -- this overlay currently runs in any context the player
# has a vehicle in, same as the Phase 1 probe before it. Only test in
# Garage/Replay/Training Room until the gate exists; see AGENTS.md
# "Behavior Constraints".


def _refreshStatsCache(vehicle):
  global g_statsCache
  g_statsCache = {
    'viewRange': stats.getEffectiveViewRange(),
    'camo': stats.getCamouflagePercentStationary(vehicle),
  }


def _overlayUpdate():
  global g_statsFrameCounter
  if not g_overlayEnabled:
    return  # toggled off -- stop rescheduling, this is the last tick
  try:
    vehicle = transform.findOwnVehicle()
    if vehicle:
      result = transform.computeWorldCheckpointsAndPorts(vehicle)
      if result:
        checkpoints, ports = result
        overlay.render(checkpoints, ports, showLabels=g_labelsEnabled)

        g_statsFrameCounter += 1
        if g_statsFrameCounter == 1 or g_statsFrameCounter % _STATS_REFRESH_EVERY_N_FRAMES == 0:
          _refreshStatsCache(vehicle)
        overlay.renderStats(checkpoints['top'], g_statsCache['viewRange'], g_statsCache['camo'])
  except Exception as e:
    # A rendering hiccup on one frame shouldn't kill the whole loop --
    # still reschedule below either way.
    log('overlay update error: ' + str(e))
  BigWorld.callback(0, _overlayUpdate)


def _logStatsSnapshot():
  try:
    viewRange = stats.getEffectiveViewRange()
    log('effective view range: ' + str(viewRange))
  except Exception as e:
    log('effective view range: ERROR ' + str(e))

  try:
    vehicle = transform.findOwnVehicle()
    if vehicle is None:
      log('camouflage % (stationary): no vehicle found')
      return
    camo = stats.getCamouflagePercentStationary(vehicle)
    log('camouflage % (stationary): ' + str(camo))
  except Exception as e:
    log('camouflage % (stationary): ERROR ' + str(e))
    return

  try:
    debugSnapshot = stats.getCamouflageDebugSnapshot(vehicle)
    if debugSnapshot is None:
      log('camo debug snapshot: unavailable')
    else:
      log('camo debug snapshot:')
      for key in ('crewLevelIncrease', 'camouflage', 'invisibility', 'eqNames', 'optionalDeviceNames',
                  'invisibilityAdditiveTerm', 'invisibilityBaseAdditive'):
        log('  %s = %s' % (key, debugSnapshot[key]))
  except Exception as e:
    log('camo debug snapshot: ERROR ' + str(e))


def _handleKeyUpEvent(event):
  global g_overlayEnabled, g_labelsEnabled
  if event.key == _TOGGLE_KEY:
    g_overlayEnabled = not g_overlayEnabled
    log('spotting overlay toggled: ' + str(g_overlayEnabled))
    if g_overlayEnabled:
      _overlayUpdate()
  elif event.key == _LABELS_TOGGLE_KEY:
    g_labelsEnabled = not g_labelsEnabled
    log('spotting overlay labels toggled: ' + str(g_labelsEnabled))
  elif event.key == _STATS_LOG_KEY:
    _logStatsSnapshot()


def init():
  global g_initDone
  if g_initDone:
    log('init() called again (double-load) -- ignoring')
    return
  g_initDone = True
  log('WotStat Spotting v' + VERSION + ' initialized. Debug mode: ' + str(DEBUG_MODE))
  InputHandler.g_instance.onKeyUp += _handleKeyUpEvent
  log('Overlay toggle bound to F4, labels toggle bound to F5, stats log bound to F6')
