from utils.logger import log

VERSION = '{{VERSION}}'
DEBUG_MODE = '{{DEBUG_MODE}}'


def init():
  """Initializes the mod. Called once by mod_wotstatSpotting.py."""
  log('WotStat Spotting v' + VERSION + ' initialized. Debug mode: ' + str(DEBUG_MODE))