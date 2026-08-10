# -*- coding: utf-8 -*-
from utils.logger import log
import BigWorld

VERSION = '{{VERSION}}'
DEBUG_MODE = '{{DEBUG_MODE}}'

def poll_for_probe():
    """Checks every 2 seconds if the vehicle is ready for probing."""
    try:
        player = BigWorld.player()
        # We need an Avatar (in battle/replay) and a vehicle with an appearance
        if player and hasattr(player, 'getOwnVehicleStabilisedMatrix'):
            vehicle = BigWorld.entity(player.playerVehicleID)
            if vehicle and vehicle.appearance and vehicle.appearance.compoundModel:
                from core import phase1_probe
                phase1_probe.run_manual_probe(vehicle)
                return # Success! Stop polling.
    except Exception:
        pass
    
    # Not ready yet, check again in 2 seconds
    BigWorld.callback(2.0, poll_for_probe)

def init():
    log('WotStat Spotting v' + VERSION + ' initialized. Debug mode: ' + str(DEBUG_MODE))
    # Start the background poller
    poll_for_probe()