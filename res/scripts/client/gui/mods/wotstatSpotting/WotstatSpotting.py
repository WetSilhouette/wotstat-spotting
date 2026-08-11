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

# Sticky: see core/transform.py's _logOnce for why -- this is the
# last-resort catch-all for anything not already specifically
# identified by transform.py/overlay.py's own sticky diagnostics below.
if 'g_overlayUpdateErrorLogged' not in globals():
  g_overlayUpdateErrorLogged = False

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
  global g_overlayUpdateErrorLogged
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
    # still reschedule below either way. Sticky/one-time: transform.py
    # and overlay.py already log specific, named failures for anything
    # they can anticipate; if execution reaches here it's something
    # neither of them caught, so log it once rather than spamming an
    # unidentified error every frame.
    if not g_overlayUpdateErrorLogged:
      g_overlayUpdateErrorLogged = True
      log('overlay update error (unidentified -- not caught more specifically '
          'in transform.py/overlay.py): ' + str(e))
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
