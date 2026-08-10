# -*- coding: utf-8 -*-
# Own-vehicle derived stats: effective view range and camouflage %.
# See NOTES.md section 21 for the research this is based on. Unlike
# core/transform.py's checkpoint formula (fully live-verified across
# many sessions), these functions rely on several BigWorld "skeletons"
# dependency-injection APIs sourced from decompiled code but NOT yet
# exercised by this project's own live testing -- every
# # TODO(api-verify) below is genuinely unconfirmed until a live log
# dump proves otherwise.
#
# All imports of the unconfirmed APIs are deferred (inside the
# functions, not at module load time) and wrapped in try/except -- if
# any of them turn out to be wrong, only these stats functions fail
# (returning None), not the whole mod. A module-level import failure
# here would otherwise cascade up through WotstatSpotting.py's
# `from core import stats` and break init() entirely, taking down the
# already-confirmed-working checkpoint overlay along with it.
#
# KNOWN LIMITATIONS (not bugs to fix -- see NOTES.md section 21 for the
# full investigation of both):
# 1. getCamouflagePercentStationary() does not include bush/foliage
#    concealment bonus. That's a server-side ray/mask system with no
#    client-exposed value -- confirmed absent from getVehicleAttrs() by
#    direct source inspection.
# 2. Some optional devices (confirmed for Low Noise Exhaust System) do
#    not appear in the live battle entity's typeDescriptor at all, so
#    their bonus is silently missing from the computed number even
#    though they're genuinely fitted. Confirmed via exact arithmetic
#    match against the Garage's own displayed value: this project's
#    output matches the "device not fitted" number precisely. Not
#    something this project's code can fix -- the input data itself
#    doesn't have it, not a formula bug. Tried the game's own
#    getClientInvisibility() as an alternative source; it requires a
#    Garage-style item object this project already confirmed is
#    fake/unsynced in battle, so that's a dead end too.
# Net effect: this can only ever report a same-or-lower camo % than the
# vehicle's true effective value, never higher. Treat it as a lower
# bound, not an exact figure.
from ..utils.logger import log


def getEffectiveViewRange():
  """
  Returns the player's own vehicle's current effective view range in
  meters (base + optics/binoculars + crew skills + damaged-optics
  penalty), or None if unavailable (e.g. not in battle, the server
  hasn't sent vehicle attrs yet, or one of the unconfirmed APIs this
  relies on doesn't exist/behave as expected). This is the SAME
  server-computed value vanilla's own minimap view-range circle uses --
  no formula reimplementation, no staleness risk from a future patch
  changing it.
  """
  try:
    from helpers import dependency  # NOTES.md section 21: confirmed against 2.3.1_EU, not top-level
    from skeletons.gui.battle_session import IBattleSessionProvider  # confirmed
    sessionProvider = dependency.instance(IBattleSessionProvider)
    vehAttrs = sessionProvider.shared.feedback.getVehicleAttrs()
    return vehAttrs.get('circularVisionRadius')
  except Exception as e:
    log('getEffectiveViewRange error: ' + str(e))
    return None


def getCamouflagePercentStationary(vehicle):
  """
  Returns the player's own vehicle's stationary camouflage % (0-100),
  or None if unavailable. First-pass implementation -- always reports
  the STATIONARY value regardless of current movement/firing state;
  see NOTES.md section 21 for the plan to add moving/at-shot switching
  once this base pipeline is confirmed live. See the module docstring
  for the bush-bonus limitation.

  NOTES.md section 21 (second fix): the original approach
  (IItemsCache.items.getItemByCD + VehicleParams) looked up a generic
  Garage-inventory item, not the live vehicle -- in battle that item is
  unsynced, so the game silently backfills a 100%-qualified, zero-skill
  fake crew and skips camo-paint/consumable lookup entirely. That's why
  it returned ~21% instead of the ~53% the Garage screen showed for the
  same, actually-equipped vehicle. This version reads directly from the
  live vehicle entity instead (typeDescriptor + real crewCompactDescrs
  + real outfit/camo + real installed consumables), the same "trust the
  live entity" pattern the checkpoint geometry already relies on.

  NOTES.md section 21 (third fix, reverted): tried
  items_utils.getClientInvisibility(vehicleDescr, vehicle, ...) as a
  cleaner alternative to the manual formula below -- it turned out to
  require a gui_items.Vehicle wrapper (it calls vehicle.getBonusCamo(),
  which only exists on that Garage-style item, not the raw battle
  entity), so it's not usable here at all. Reverted to the manual
  computeBaseInvisibility()/getInvisibility() sequence.

  KNOWN LIMITATION (second one, not fixable from here either): some
  optional devices -- confirmed for Low Noise Exhaust System -- do not
  show up in vehicle.typeDescriptor.optionalDevices /
  miscAttrs['invisibilityAdditiveTerm'] on the live battle entity
  (confirmed by direct log: both read 0.0 while the device was fitted
  and contributing +0.08 in the Garage's own display). This function
  therefore under-reports camo by that device's bonus when it's
  fitted, same category of gap as the bush-bonus limitation -- an
  input-data gap this project's code can't see, not a formula bug.
  """
  try:
    from constants import VEHICLE_TTC_ASPECTS
    from items.vehicles import vehicleAttributeFactors
    from items import utils as items_utils

    vehicleDescr = vehicle.typeDescriptor
    crewCompactDescrs = list(vehicle.crewCompactDescrs)  # real trained skills/perks, not a fake crew

    from helpers import dependency
    from skeletons.gui.battle_session import IBattleSessionProvider
    sessionProvider = dependency.instance(IBattleSessionProvider)
    equipmentController = sessionProvider.shared.equipments
    eqs = [item.getDescriptor() for item in equipmentController.getEquipments().values() if item is not None]

    factors = vehicleAttributeFactors()
    items_utils.updateAttrFactorsWithSplit(vehicleDescr, crewCompactDescrs, eqs, factors)

    camouflageId = None
    from vehicle_systems import camouflages
    from items.components.c11n_constants import ApplyArea
    outfitComponent = camouflages.getOutfitComponent(vehicle.publicInfo.outfit, vehicleDescr)
    for camo in outfitComponent.camouflages:
      if camo.appliedTo & ApplyArea.HULL:
        camouflageId = camo.id
        break

    baseInvisibility = vehicleDescr.computeBaseInvisibility(factors['camouflage'], camouflageId)
    savedInvisibilityFactors = factors['invisibility']
    factors['invisibility'] = savedInvisibilityFactors[VEHICLE_TTC_ASPECTS.WHEN_STILL]
    stillPercent = items_utils.getInvisibility(vehicleDescr, factors, baseInvisibility, False) * 100.0
    factors['invisibility'] = savedInvisibilityFactors
    return stillPercent
  except Exception as e:
    log('getCamouflagePercentStationary error: ' + str(e))
    return None


def getCamouflageDebugSnapshot(vehicle):
  """
  Diagnostic-only: exposes the intermediate values behind
  getCamouflagePercentStationary(), to pin down the remaining gap
  against the Garage's displayed value (NOTES.md section 21 -- 44%
  computed vs. 52.87% Garage-displayed, ~9 points still unexplained).
  Not used by getCamouflagePercentStationary() itself. Returns None on
  any failure, same as everything else in this file.
  """
  try:
    from helpers import dependency
    from skeletons.gui.battle_session import IBattleSessionProvider
    from items.vehicles import vehicleAttributeFactors
    from items import utils as items_utils

    vehicleDescr = vehicle.typeDescriptor
    crewCompactDescrs = list(vehicle.crewCompactDescrs)

    sessionProvider = dependency.instance(IBattleSessionProvider)
    equipmentController = sessionProvider.shared.equipments
    eqItems = [item for item in equipmentController.getEquipments().values() if item is not None]
    eqs = [item.getDescriptor() for item in eqItems]

    factors = vehicleAttributeFactors()
    items_utils.updateAttrFactorsWithSplit(vehicleDescr, crewCompactDescrs, eqs, factors)

    optionalDeviceNames = [getattr(d, 'name', str(d)) for d in vehicleDescr.optionalDevices if d is not None]
    eqNames = [getattr(e, 'name', str(e)) for e in eqs]

    return {
      'crewLevelIncrease': factors.get('crewLevelIncrease'),
      'camouflage': factors.get('camouflage'),
      'invisibility': factors.get('invisibility'),
      'eqNames': eqNames,
      'optionalDeviceNames': optionalDeviceNames,
      # NOTES.md section 21, third fix: Low Noise Exhaust System's bonus
      # lands here -- should be 0.08 for a REGULAR-slot device if
      # vehicleDescr correctly reflects the fitted equipment.
      'invisibilityAdditiveTerm': vehicleDescr.miscAttrs.get('invisibilityAdditiveTerm'),
      'invisibilityBaseAdditive': vehicleDescr.miscAttrs.get('invisibilityBaseAdditive'),
    }
  except Exception as e:
    log('getCamouflageDebugSnapshot error: ' + str(e))
    return None
