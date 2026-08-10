# -*- coding: utf-8 -*-
# BigWorld/game-API glue for resolving own-vehicle checkpoint/port world
# positions. Pairs with core/geometry.py (pure math, no game-API
# imports). Every API call here was confirmed against a live client --
# see NOTES.md sections 10-15 for sourcing and validation.
#
# Battle/Replay/Training Room only -- Garage is explicitly out of scope
# for now (NOTES.md section 15). Don't re-add Garage handling here
# without deliberately revisiting that decision.
import BigWorld
import Math

from . import geometry
from . import exposure
from ..utils.logger import log

_NODE_NAMES = ('hull', 'turret')


def findOwnVehicle():
  # NOTES.md section 10: player.playerVehicleID -> BigWorld.entity(id)
  # is the confirmed battle-context path to the player's own vehicle.
  try:
    player = BigWorld.player()
    if player and hasattr(player, 'playerVehicleID'):
      vehicle = BigWorld.entity(player.playerVehicleID)
      if vehicle and getattr(vehicle, 'appearance', None) and vehicle.appearance.compoundModel:
        return vehicle
  except Exception as e:
    log('findOwnVehicle error: ' + str(e))
  return None


def getNodeMatrices(vehicle):
  # NOTES.md section 10: compoundModel.node(name) wrapped in
  # Math.Matrix(...) is the confirmed, stable way to get live
  # world-space hull/turret matrices (validated across multiple
  # sessions, including while the vehicle was moving and rotating).
  matrices = {}
  compoundModel = vehicle.appearance.compoundModel
  for name in _NODE_NAMES:
    node = compoundModel.node(name)
    if node is not None:
      matrices[name] = Math.Matrix(node)
  return matrices


def getHullTurretBbox(descr):
  # NOTES.md section 13: None for the first ~2-3s after spawning in
  # battle, then self-populates automatically -- no extra code needed.
  # Callers should treat a None result as "not ready yet", not an
  # error.
  return descr.hull.hitTester.bbox, descr.turret.hitTester.bbox


def computeWorldCheckpointsAndPorts(vehicle):
  """
  Returns (checkpoints, ports, exposures) on success, or None if the
  vehicle's collision/model data isn't ready yet (normal for the first
  couple seconds after spawn -- callers should retry, not treat this as
  an error). checkpoints is a dict of geometry.CHECKPOINT_NAMES -> world
  Math.Vector3; ports is a dict of geometry.PORT_NAMES -> world
  Math.Vector3; exposures is a dict of geometry.CHECKPOINT_NAMES ->
  one of exposure.EXPOSURE_BUCKETS, classified from the same local
  offsets before the world-space projection (see
  exposure.classifyExposure -- purely self-referential, never uses
  enemy data).
  """
  try:
    descr = vehicle.typeDescriptor
    hullBbox, turretBbox = getHullTurretBbox(descr)
    if hullBbox is None or turretBbox is None:
      return None

    nodeMatrices = getNodeMatrices(vehicle)
    hullMatrix = nodeMatrices.get('hull')
    turretMatrix = nodeMatrices.get('turret')
    if hullMatrix is None or turretMatrix is None:
      return None

    hullBboxMin, hullBboxMax = hullBbox[0], hullBbox[1]
    turretPosOnHull = descr.hull.turretPositions[0]
    turretBboxMax = turretBbox[1]
    gunPosition = descr.turret.gunPosition

    # NOTES.md section 19: chassis.hullPosition is deliberately NOT
    # passed here -- node('hull') already bakes it in, so adding it
    # again would double-count it (confirmed live: floated every
    # checkpoint by exactly chassis.hullPosition.y).
    localCheckpoints, observerOnChassis = geometry.computeLocalCheckpoints(
        hullBboxMin, hullBboxMax, turretPosOnHull, turretBboxMax, gunPosition)

    worldCheckpoints = {}
    for name in geometry.CHECKPOINT_NAMES:
      worldCheckpoints[name] = hullMatrix.applyPoint(Math.Vector3(*localCheckpoints[name]))
    exposures = exposure.classifyAllExposures(localCheckpoints)

    worldPorts = {
      'chassis': hullMatrix.applyPoint(Math.Vector3(*observerOnChassis)),
      'turret': turretMatrix.applyPoint(gunPosition),
    }

    return worldCheckpoints, worldPorts, exposures
  except Exception as e:
    log('computeWorldCheckpointsAndPorts error: ' + str(e))
    return None


def getDebugSnapshot(vehicle):
  """
  Diagnostic-only: returns every raw input to the checkpoint formula
  (not just the final world-space results), so a rendering discrepancy
  can be traced back to a specific value instead of guessed at. Not
  used by computeWorldCheckpointsAndPorts() itself -- callers should
  treat this as "for a debug log line", not real functionality. Returns
  None under the same not-ready conditions as computeWorldCheckpointsAndPorts.
  """
  try:
    descr = vehicle.typeDescriptor
    hullBbox, turretBbox = getHullTurretBbox(descr)
    if hullBbox is None or turretBbox is None:
      return None
    nodeMatrices = getNodeMatrices(vehicle)
    return {
      'nodeHullPos': nodeMatrices['hull'].translation if 'hull' in nodeMatrices else None,
      'nodeTurretPos': nodeMatrices['turret'].translation if 'turret' in nodeMatrices else None,
      'chassisHullPosition': descr.chassis.hullPosition,
      'hullBboxMin': hullBbox[0],
      'hullBboxMax': hullBbox[1],
      'turretPosOnHull': descr.hull.turretPositions[0],
      'turretBboxMin': turretBbox[0],
      'turretBboxMax': turretBbox[1],
      'gunPosition': descr.turret.gunPosition,
    }
  except Exception as e:
    log('getDebugSnapshot error: ' + str(e))
    return None
