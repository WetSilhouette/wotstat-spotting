# -*- coding: utf-8 -*-
import BigWorld
import Math
import ResMgr
from ..utils.logger import log

def _f(v):
    if v is None: return "None"
    try: return "(%.3f, %.3f, %.3f)" % (v[0], v[1], v[2])
    except: return str(v)

def run_manual_probe(vehicle):
    log("===== Phase 1: Deep Extraction Started =====")
    try:
        descr = vehicle.typeDescriptor
        # 1. IDENTIFY COMPONENTS
        nation_name, tank_name = descr.type.name.split(':')
        xml_path = 'scripts/item_defs/vehicles/' + nation_name + '/' + tank_name + '.xml'
        log("Target XML: " + xml_path)

        # 2. READ RAW XML (The only way to get the 8 points in 2.3+)
        section = ResMgr.openSection(xml_path)
        if section:
            # Checkpoints are usually in the <hull> and <turret0> sections
            hull_xml = section['hull']
            if hull_xml and hull_xml.has_key('visibilityCheckPoints'):
                log("Hull Checkpoints (XML):")
                for node in hull_xml['visibilityCheckPoints'].values():
                    log("  -> " + node.asString)
            
            # Turrets are nested in turrets0 -> turret0
            if section.has_key('turrets0'):
                turr_xml = section['turrets0'].values()[0]
                if turr_xml and turr_xml.has_key('visibilityCheckPoints'):
                    log("Turret Checkpoints (XML):")
                    for node in turr_xml['visibilityCheckPoints'].values():
                        log("  -> " + node.asString)

            # Vision Ports (Observer positions)
            if hull_xml and hull_xml.has_key('observerPos'):
                log("Static Port (XML): " + hull_xml['observerPos'].asString)
            if turr_xml and turr_xml.has_key('observerPos'):
                log("Dynamic Port (XML): " + turr_xml['observerPos'].asString)
        
        # 3. NODE SKELETON SEARCH (Find the Turret Matrix)
        # Modern WoT uses a CompoundModel. We need to know which node tracks the turret.
        compound = vehicle.appearance.compoundModel
        log("Model Nodes Search:")
        for node_name in ['hull', 'turret', 'gun', 'HP_turretJoint']:
            try:
                node = compound.node(node_name)
                mat = Math.Matrix(node)
                log("  Node [%s] world pos: %s" % (node_name, _f(mat.translation)))
            except:
                log("  Node [%s]: NOT FOUND" % node_name)

    except Exception as e:
        log("Probe CRASHED: " + str(e))
    log("===== Phase 1: Deep Extraction End =====")

def install():
    def _poll():
        player = BigWorld.player()
        if player and hasattr(player, 'playerVehicleID'):
            veh = BigWorld.entity(player.playerVehicleID)
            if veh and veh.appearance:
                run_manual_probe(veh)
                return
        BigWorld.callback(1.0, _poll)
    _poll()