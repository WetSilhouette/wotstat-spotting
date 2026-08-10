# -*- coding: utf-8 -*-
# Verification wrapper, not real functionality: logs the result of the
# real implementation (core/geometry.py + core/transform.py) against a
# live vehicle, so the Phase 1 -> Phase 2 migration can be re-checked
# once more before this file is deleted for good (per AGENTS.md: "not
# part of the release feature set -- delete or gut this file once Phase
# 1 is marked fully confirmed"). See NOTES.md sections 10-15.
from . import geometry
from . import transform
from ..utils.logger import log


def _fmtVec(v):
  if v is None:
    return 'None'
  try:
    return '(%.3f, %.3f, %.3f)' % (v[0], v[1], v[2])
  except Exception:
    return str(v)


def findOwnVehicle():
  return transform.findOwnVehicle()


def runManualProbe(vehicle):
  log('===== geometry/transform migration check =====')
  result = transform.computeWorldCheckpointsAndPorts(vehicle)
  if result is None:
    log('  not ready yet (collision data still None -- normal for the first couple seconds after spawn)')
    log('===== end =====')
    return
  checkpoints, ports = result
  for name in geometry.CHECKPOINT_NAMES:
    log('  checkpoint[%s] -> world: %s' % (name, _fmtVec(checkpoints[name])))
  for name in geometry.PORT_NAMES:
    log('  port[%s] -> world: %s' % (name, _fmtVec(ports[name])))
  log('===== end =====')
