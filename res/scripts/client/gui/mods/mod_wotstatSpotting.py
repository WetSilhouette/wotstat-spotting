# -*- coding: utf-8 -*-
"""Entry point for the WotStat Spotting Visualizer mod.

Kept intentionally thin: it only wires up the import and the call to
init(). Real logic lives in wotstatSpotting/WotstatSpotting.py.

If anything here fails -- including the import itself -- we fall back
to a bare print() rather than utils.logger.log(), since the failure
could be exactly what's breaking that import path. This guarantees a
failure at load time is never fully silent.
"""

try:
  from wotstatSpotting.WotstatSpotting import init
  init()
except Exception as e:
  print('[WOTSTAT-SPOTTING] FATAL: failed to initialize mod: ' + str(e))