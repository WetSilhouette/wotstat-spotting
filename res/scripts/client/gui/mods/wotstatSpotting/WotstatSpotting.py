# -*- coding: utf-8 -*-
from utils.logger import log
import BigWorld
import Keys
from gui import InputHandler

from core import transform
from core import overlay

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

# F2/F3 are already used by wotstat-vegetation's own toggle keys (see
# CONCEPT.md: "pick unused keys to avoid conflicts if both mods are
# installed together").
_TOGGLE_KEY = Keys.KEY_F4
_LABELS_TOGGLE_KEY = Keys.KEY_F5

# NOTE: no restriction-gate check yet (utils/restriction.py is Phase 3,
# still empty) -- this overlay currently runs in any context the player
# has a vehicle in, same as the Phase 1 probe before it. Only test in
# Garage/Replay/Training Room until the gate exists; see AGENTS.md
# "Behavior Constraints".


def _overlayUpdate():
  if not g_overlayEnabled:
    return  # toggled off -- stop rescheduling, this is the last tick
  try:
    vehicle = transform.findOwnVehicle()
    if vehicle:
      result = transform.computeWorldCheckpointsAndPorts(vehicle)
      if result:
        checkpoints, ports, exposures = result
        overlay.render(checkpoints, ports, exposures=exposures, showLabels=g_labelsEnabled)
  except Exception as e:
    # A rendering hiccup on one frame shouldn't kill the whole loop --
    # still reschedule below either way.
    log('overlay update error: ' + str(e))
  BigWorld.callback(0, _overlayUpdate)


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


def init():
  global g_initDone
  if g_initDone:
    log('init() called again (double-load) -- ignoring')
    return
  g_initDone = True
  log('WotStat Spotting v' + VERSION + ' initialized. Debug mode: ' + str(DEBUG_MODE))
  InputHandler.g_instance.onKeyUp += _handleKeyUpEvent
  log('Overlay toggle bound to F4, labels toggle bound to F5')
