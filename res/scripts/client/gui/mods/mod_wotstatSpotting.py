try:
  from wotstatSpotting.WotstatSpotting import init
  init()
except Exception as e:
  print('[WOTSTAT-SPOTTING] FATAL: failed to initialize mod: ' + str(e))