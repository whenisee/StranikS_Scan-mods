﻿# -*- coding: utf-8 -*-

__author__  = 'StranikS_Scan'
__version__ = 'V1.2.0 P2.7 W1.5.1 28.07.2019'

import BigWorld, Event
from BattleReplay import g_replayCtrl
from Avatar import PlayerAvatar
from Vehicle import Vehicle
from items import vehicles
from vehicle_systems.tankStructure import TankPartIndexes
from constants import ARENA_GUI_TYPE_LABEL, ARENA_BONUS_TYPE, VEHICLE_HIT_EFFECT
from gui.shared.utils.functions import getArenaGeomentryName
from items.components.c11n_constants import SeasonType, SeasonTypeNames
from VehicleEffects import DamageFromShotDecoder
from helpers.time_utils import getTimeLeftFormat

import re
import os, codecs, json
import unicodedata
from datetime import datetime
from Math import Matrix, Vector3

# Consts and Vars ..........................................................................

APPLICATION_ID = 'eJwzTExNMTFKTDU2szRITTUwT7EwMzSzSEwyMjcxtDRLMgUAk5oIkw=='.decode('base64').decode('zlib')

CONFIG_VERSION = '1.1'
CSV_VERSION    = '1.4'

LOG_BATTLES = LOG_PLAYERS = LOG_EVENTS = UNIQUE_SUBDIR = False
CONFIG_FILENAME = LOG_DIR = LOG_BATTLES_FILENAME = LOG_PLAYERS_FILENAME = LOG_EVENTS_FILENAME = None

COLLIDE_INDENT = 5.0  #>----x
COLLIDE_LENGTH = 10.0 #     x----> 

COLLIDE_MULTI  = False
COLLIDE_SCHEME = 'cross'
COLLIDE_SCALE = 1.0

# Classes and functions ===========================================================

def getLogPath(dirname):
    if dirname:
        dirname = dirname.replace('\\', '/')
        if dirname[-1] != '/':
            dirname += '/'
    path = ('./mods/' if ':' not in dirname else '') + dirname
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except:
            path = './mods/'
    return path

def getConfigFileName():
    filename = './mods/configs/SimpleLogger/SimpleLogger.cfg'
    return filename if os.path.exists(filename) else None

def removeAccents(value): 
    return u"".join([c for c in unicodedata.normalize('NFKD', unicode(value)) if not unicodedata.combining(c)])

def tankTypeAbb(tag):
    return 'MT' if 'mediumTank' == tag else 'HT' if 'heavyTank'== tag else 'AT' if 'AT-SPG' == tag else 'SPG' if 'SPG' == tag else 'LT'

def shellTypeAbb(name):
    return 'APCR' if name == 'ARMOR_PIERCING_CR' else 'HE' if name == 'HIGH_EXPLOSIVE' else 'HC' if name == 'HOLLOW_CHARGE' else 'AP' #ARMOR_PIERCING, ARMOR_PIERCING_HE

def printStrings(filename, value): 
    if filename is not None:
        with codecs.open(filename, 'a', 'utf-8-sig') as file:
            if isinstance(value, list) or isinstance(value, tuple):
                file.write(';'.join(value) + '\n')
            else:
                file.write(value + '\n')

def getTimeLeft():
    time = g_replayCtrl.getArenaLength() if g_replayCtrl.isPlaying else BigWorld.player().arena.periodEndTime - BigWorld.serverTime()
    return '00:'+getTimeLeftFormat(time), ('%.3f' % time).replace('.',',')

BONUS_TYPE_NAMES = {getattr(ARENA_BONUS_TYPE, k):k for k in dir(ARENA_BONUS_TYPE)[::-1] if not k.startswith('_') and isinstance(getattr(ARENA_BONUS_TYPE, k), int)}
VEHICLE_HIT_EFFECT_NAMES = {getattr(VEHICLE_HIT_EFFECT, k):k for k in dir(VEHICLE_HIT_EFFECT)[::-1] if not k.startswith('_') and isinstance(getattr(VEHICLE_HIT_EFFECT, k), int)}

class _CSHexahedron(object):
    NAME = 'hexahedron'
    directions = property(lambda self: self.__dirVectors)

    def __init__(self, width, height, depth, scale):
        self.__scale = scale
        self.__width  = round(width * self.__scale, 3)
        self.__height = round(height * self.__scale, 3)
        self.__depth  = round(depth * self.__scale, 3)
        self.__dirVectors = [Vector3(0.0, 0.0, 0.0),
                             Vector3(self.__width, self.__height, -self.__depth),
                             Vector3(self.__width, -self.__height, -self.__depth),
                             Vector3(-self.__width, -self.__height, -self.__depth),
                             Vector3(-self.__width, self.__height, -self.__depth),
                             Vector3(self.__width, self.__height, self.__depth),
                             Vector3(self.__width, -self.__height, self.__depth),
                             Vector3(-self.__width, -self.__height, self.__depth),
                             Vector3(-self.__width, self.__height, self.__depth)]
        self.__dirNames = ['Center', 
                           'Up-Right-Back',
                           'Down-Right-Back',
                           'Down-Left-Back',
                           'Up-Left-Back',
                           'Up-Right-Forward',
                           'Down-Right-Forward',
                           'Down-Left-Forward',
                           'Up-Left-Forward']

    def format(self, layers):
        return '{scheme: %s, (dW,dH,dD): (%.3f,%.3f,%.3f), scale: %s, layers: {%s}}' % (self.NAME, self.__width, self.__height, self.__depth, self.__scale, \
               ', '.join('%s: %s' % (self.__dirNames[i], layer) for i, layer in enumerate(layers) if layer))

class _CSCross(object):
    NAME = 'cross'
    directions = property(lambda self: self.__dirVectors)

    def __init__(self, width, height, depth, scale):
        self.__scale = scale
        self.__width  = round(width * self.__scale, 3)
        self.__height = round(height * self.__scale, 3)
        self.__depth  = round(depth * self.__scale, 3) 
        self.__dirVectors = [Vector3(0.0, 0.0, 0.0),
                             Vector3(0.0, self.__height, 0.0),
                             Vector3(self.__width, 0.0, 0.0),
                             Vector3(0.0, -self.__height, 0.0),
                             Vector3(-self.__width, 0.0, 0.0),
                             Vector3(0.0, 0.0, -self.__depth),
                             Vector3(0.0, 0.0, self.__depth)]
        self.__dirNames = ['Center', 
                           'Up',
                           'Right',
                           'Down',
                           'Left',
                           'Back',
                           'Forward']

    def format(self, layers):
        return '{scheme: %s, (dW,dH,dD): (%.3f,%.3f,%.3f), scale: %s, layers: {%s}}' % (self.NAME, self.__width, self.__height, self.__depth, self.__scale, \
               ', '.join('%s: %s' % (self.__dirNames[i], layer) for i, layer in enumerate(layers) if layer))

class _CSCenter(object):
    NAME = 'center'
    directions = property(lambda self: self.__dirVectors)

    def __init__(self):
        self.__dirVectors = [Vector3(0.0, 0.0, 0.0)]
        self.__dirNames = ['Center']

    def format(self, layers):
        return '%s' % layers

# CSV -----------------------------------------------------------------

BATTLES_HEADER = ('"arenaUniqueID"','"dateTime"','"serverName"','"playerDBID"', '"userName"', '"vehicleTypeTag"', '"vehicleTypeNFKD"', '"vehicleLevel"',
                  '"arenaGuiType"','"arenaTypeID"','"arenaBonusType"','"arenaKind"','"battleLevel"') + \
                 ('"allyTanksCount"','"enemyTanksCount"','"allyTeamHP"','"enemyTeamHP"','"allyTanksAvgLevel"','"enemyTanksAvgLevel"')
PLAYERS_HEADER = ('"arenaUniqueID"','"accountDBID"','"userName"','"isEnemy"','"vehicleTypeTag"','"vehicleTypeNFKD"','"level"','"hp"') + \
                 ('"BATTLES"','"WINS"','"EXP"','"DAMAGE"','"FRAGS"','"SPOTTED"','"CAPTURE"','"DEFENSE"','"ACCURACY"','"SURVIVED"',"WN8","EFF","XTE",
                  '"battles"','"wins"','"experience"','"damage"','"frags"','"spot"','"capture"','"defense"','"accuracy"','"survived"','"wn8"','"eff"','"xte"',
                  '"WN8(XVM)"','"WGR(XVM)"','"WTR(XVM)"')
EVENTS_HEADER =  ('"arenaUniqueID"','"timeLeft"','"timeLeftSec"','"event"','"userDBID"','"attakerDBID"','"initialInfo"','"shellInfo"','"decodeInfo"')

PLAYERS_STAT_COLLECT = {}

def onBattleLoaded(statistic):
    global LOG_BATTLES_FILENAME, LOG_PLAYERS_FILENAME, LOG_EVENTS_FILENAME
    if UNIQUE_SUBDIR:
        logName = 'temp'
        replayFileName = g_replayCtrl.getAutoStartFileName()
        if replayFileName is not None and replayFileName != '':
            logName, _ = os.path.splitext(os.path.basename(replayFileName))
        logPath = getLogPath(LOG_DIR + '/'+ logName + '_' + datetime.now().strftime('%d%m%y%H%M%S%f')[:15])
    else:
        logPath = getLogPath(LOG_DIR)
    LOG_BATTLES_FILENAME = logPath + 'sl_battles_ver_%s.csv' % CSV_VERSION
    LOG_PLAYERS_FILENAME = logPath + 'sl_players_ver_%s.csv' % CSV_VERSION
    LOG_EVENTS_FILENAME = logPath + 'sl_events_ver_%s.csv' % CSV_VERSION
    if LOG_BATTLES and not os.path.exists(LOG_BATTLES_FILENAME):
        printStrings(LOG_BATTLES_FILENAME, BATTLES_HEADER)
    if LOG_PLAYERS and not os.path.exists(LOG_PLAYERS_FILENAME):
        printStrings(LOG_PLAYERS_FILENAME, PLAYERS_HEADER)
    if LOG_EVENTS and not os.path.exists(LOG_EVENTS_FILENAME):
        printStrings(LOG_EVENTS_FILENAME, EVENTS_HEADER)
    #--------------
    if LOG_BATTLES:
        player = BigWorld.player()
        araneInfo = None
        if g_replayCtrl.isPlaying or g_replayCtrl.isRecording:
            arenaInfo = g_replayCtrl._BattleReplay__replayCtrl.getArenaInfoStr()
            if arenaInfo and isinstance(arenaInfo, str):
                try:
                    arenaInfo = json.loads(arenaInfo)
                except:
                    pass
        if arenaInfo:
            dateTime = arenaInfo.get('dateTime','')
            serverName = arenaInfo.get('serverName','')
        else:
            now = datetime.now()
            dateTime = '%02d.%02d.%04d %02d:%02d:%02d' % (now.day, now.month, now.year, now.hour, now.minute, now.second)
            serverName = g_replayCtrl.connectionMgr.serverUserName
        vType = statistic.base[player.playerVehicleID]
        battleInfo = ('%s'   % player.arenaUniqueID,
                      dateTime,
                      '"%s"' % serverName,
                      '%s'   % vType.get('accountDBID', '-'),
                      '"%s"' % vType['userName'],
                      '"%s"' % tankTypeAbb(vType['type']['tag']),
                      '"%s"' % vType['name'],
                      '%d'   % vType['level'],
                      '"%s(%d)"' % (ARENA_GUI_TYPE_LABEL.LABELS.get(player.arenaGuiType), player.arenaGuiType),
                      '"%s(%d)"' % (getArenaGeomentryName(player.arenaTypeID), player.arenaTypeID),
                      '"%s(%d)"' % (BONUS_TYPE_NAMES.get(player.arenaBonusType), player.arenaBonusType),
                      '"%s(%d)"' % (SeasonTypeNames[SeasonType.fromArenaKind(player.arenaExtraData['arenaKind'])], player.arenaExtraData['arenaKind']),
                      ('%d'  % player.arenaExtraData['battleLevel']) if 'battleLevel' in player.arenaExtraData else '-',
                      #--------------
                      '%d' % statistic.allyTanksCount,
                      '%d' % statistic.enemyTanksCount,
                      '%d' % statistic.allyTeamHP,
                      '%d' % statistic.enemyTeamHP,
                      ('%.3f' % (sum([value['level'] for value in statistic.base.itervalues() if not value['isEnemy']]) / float(statistic.allyTanksCount))).replace('.',','),
                      ('%.3f' % (sum([value['level'] for value in statistic.base.itervalues() if value['isEnemy']]) / float(statistic.enemyTanksCount))).replace('.',','))
        printStrings(LOG_BATTLES_FILENAME, battleInfo)

def onWGBattleLoaded(statistic):
    if LOG_PLAYERS:
        player = BigWorld.player()
        if not player or not hasattr(player, 'isOnArena'):
            return
        global PLAYERS_STAT_COLLECT
        PLAYERS_STAT_COLLECT['WG'] = {}
        statistic = {x['account_id']: x for x in statistic['players']} if statistic and statistic.has_key('players') else {}
        for vType in g_TanksStatistic.base.values():
            accountDBID = vType.get('accountDBID')
            playerInfo = ['%s'   % BigWorld.player().arenaUniqueID,
                          '%s'   % accountDBID if accountDBID else '-',
                          '"%s"' % vType['userName'],
                          '%d'   % vType['isEnemy'],
                          '"%s"' % tankTypeAbb(vType['type']['tag']),
                          '"%s"' % vType['name'],
                          '%d'   % vType['level'],
                          '%d'   % vType['hp']]
            pStat = statistic.get(accountDBID, {}) if accountDBID else {}
            playerStat = ['%d' % pStat['battles'] if pStat['battles'] else '',
                          '%d' % pStat['wins'] if pStat['wins'] else '',
                          '%d' % pStat['xp'] if pStat['xp'] else '',
                          '%d' % pStat['damage_dealt'] if pStat['damage_dealt'] else '',
                          '%d' % pStat['frags'] if pStat['frags'] else '',
                          '%d' % pStat['spotted'] if pStat['spotted'] else '',
                          '%d' % pStat['capture_points'] if pStat['capture_points'] else '',
                          '%d' % pStat['dropped_capture_points'] if pStat['dropped_capture_points'] else '',
                          ('%.2f' % pStat['hits_percents']).replace('.',',') if pStat['hits_percents'] else '',
                          '%d' % pStat['survived_battles'] if pStat['survived_battles'] else '',
                          '%d' % round(max(g_Calculator.WN8(pStat),0)),
                          '%d' % round(max(g_Calculator.EFF(pStat),0)),
                          '%d' % round(max(g_Calculator.XTE(pStat['vehicles']),0)) if pStat['vehicles'] else 0] if pStat else [''] * 13
            if 'vehicles' in pStat:
                pStat = pStat['vehicles'].get(vType['tank_id'], {}) if pStat['vehicles'] else {}
            tankStat = ['%d' % pStat['battles'] if pStat['battles'] else '',
                        '%d' % pStat['wins'] if pStat['wins'] else '',
                        '%d' % pStat['xp'] if pStat['xp'] else '',
                        '%d' % pStat['damage_dealt'] if pStat['damage_dealt'] else '',
                        '%d' % pStat['frags'] if pStat['frags'] else '',
                        '%d' % pStat['spotted'] if pStat['spotted'] else '',
                        '%d' % pStat['capture_points'] if pStat['capture_points'] else '',
                        '%d' % pStat['dropped_capture_points'] if pStat['dropped_capture_points'] else '',
                        ('%.2f' % pStat['hits_percents']).replace('.',',') if pStat['hits_percents'] else '',
                        '%d' % pStat['survived_battles'] if pStat['survived_battles'] else '',
                        '%d' % round(max(g_Calculator.wn8(pStat),0)),
                        '%d' % round(max(g_Calculator.eff(pStat),0)),
                        '%d' % round(max(g_Calculator.xte(pStat),0))] if pStat else [''] * 13
            if accountDBID:
                PLAYERS_STAT_COLLECT['WG'][accountDBID] = playerInfo + playerStat + tankStat
        if 'XVM' in PLAYERS_STAT_COLLECT:
            for id in PLAYERS_STAT_COLLECT['WG']:
                if id in PLAYERS_STAT_COLLECT['XVM']:
                    printStrings(LOG_PLAYERS_FILENAME, PLAYERS_STAT_COLLECT['WG'][id] + PLAYERS_STAT_COLLECT['XVM'][id])
                else:
                    printStrings(LOG_PLAYERS_FILENAME, PLAYERS_STAT_COLLECT['WG'][id])
            PLAYERS_STAT_COLLECT.clear()

def onXVMBattleLoaded(statistic):
    if LOG_PLAYERS:
        player = BigWorld.player()
        if not player or not hasattr(player, 'isOnArena'):
            return
        global PLAYERS_STAT_COLLECT
        PLAYERS_STAT_COLLECT['XVM'] = {}
        statistic = {x['_id']: x for x in statistic['players']} if statistic and statistic.has_key('players') else {}
        for vType in g_TanksStatistic.base.values():
            accountDBID = vType.get('accountDBID')
            pStat = statistic.get(accountDBID) if accountDBID else {}
            PLAYERS_STAT_COLLECT['XVM'][accountDBID] = ['%d' % pStat['wn8'] if pStat['wn8'] else '',
                                                        '%d' % pStat['wgr'] if pStat['wgr'] else '',
                                                        '%d' % pStat['wtr'] if pStat['wtr'] else ''] if pStat else [''] * 3
        if 'WG' in PLAYERS_STAT_COLLECT:
            for id in PLAYERS_STAT_COLLECT['WG']:
                if id in PLAYERS_STAT_COLLECT['XVM']:
                    printStrings(LOG_PLAYERS_FILENAME, PLAYERS_STAT_COLLECT['WG'][id] + PLAYERS_STAT_COLLECT['XVM'][id])
                else:
                    printStrings(LOG_PLAYERS_FILENAME, PLAYERS_STAT_COLLECT['WG'][id])
            PLAYERS_STAT_COLLECT.clear()

try:
    from gui.mods.methods.hook import g_overrideLib
    from gui.mods.xvm_statistics import g_XVMStatisticsEvents
    from gui.mods.wg_statistics import g_WGStatisticsEvents
    from gui.mods.victory_chances import g_StatisticEvents, g_TanksStatistic
    from gui.mods.rating_calculation import g_Calculator
except:
    print '[%s] Loading mod: Not found "mod.NetStatisticsModules", loading stoped!' % __author__
else:
    g_WGStatisticsEvents.addStatsFullBattleLoaded(APPLICATION_ID, onWGBattleLoaded)
    g_XVMStatisticsEvents.addStatsBattleLoaded(APPLICATION_ID, onXVMBattleLoaded)
    g_StatisticEvents.onBattleLoaded += onBattleLoaded

    CONFIG_FILENAME = getConfigFileName()
    if CONFIG_FILENAME is not None:
        #Config ------------------------------------------
        config = json.loads(re.compile('(/\*(.|\n)*?\*/)|((#|//).*?$)', re.I | re.M).sub('', codecs.open(CONFIG_FILENAME, 'r', 'utf-8-sig').read()))
        if 'System' in config and 'Version' in config['System'] and config['System']['Version'] == CONFIG_VERSION:
            LOG_DIR = config['Log']['Dir']
            UNIQUE_SUBDIR = config['Log']['UniqueSubDir']
            LOG_BATTLES = config['Log']['Files']['Battles']
            LOG_PLAYERS = config['Log']['Files']['Players']
            LOG_EVENTS = config['Log']['Files']['Events']
            #Collider ---
            COLLIDE_INDENT = config['Mechanics']['ShotsCollider']['CollideIndent']
            COLLIDE_LENGTH = config['Mechanics']['ShotsCollider']['CollideLength']
            COLLIDE_MULTI = config['Mechanics']['ShotsCollider']['MultiCollide']['Enable']
            COLLIDE_SCHEME = config['Mechanics']['ShotsCollider']['MultiCollide']['Scheme'].lower()
            COLLIDE_SCALE = config['Mechanics']['ShotsCollider']['MultiCollide']['ShapeScale']

    # Hooks ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    @g_overrideLib.registerEvent(PlayerAvatar, 'showTracer')
    def new_showTracer(self, shooterID, shotID, isRicochet, effectsIndex, refStartPoint, velocity, gravity, maxShotDist, *a, **k):
        if LOG_EVENTS and shooterID > 0:
            #Initial info
            timeLeft, timeLeftSec = getTimeLeft()
            eventInfo = ['%s' % self.arenaUniqueID, timeLeft, timeLeftSec,
                         '"PlayerAvatar.showTracer"',
                         '%s' % self.arena.vehicles[shooterID].get('accountDBID', '-'),
                         '',
                         json.dumps({'shotID': shotID, 'isRicochet': isRicochet, 'effectsIndex': effectsIndex,
                                     'velocity': round(velocity.length/0.8, 3), 'gravity': round(gravity/0.64, 3), 'maxShotDist': maxShotDist})]
            #Decode info
            shellInfo = {}
            for shot in self.arena.vehicles[shooterID]['vehicleType'].gun.shots:
                if effectsIndex == shot.shell.effectsIndex:
                    shellInfo['name'] = shot.shell.name
                    shellInfo['kind'] = shellTypeAbb(shot.shell.kind)
                    shellInfo['damage'] = str(shot.shell.damage)
                    shellInfo['caliber'] = shot.shell.caliber
                    shellInfo['piercingPower'] = str(shot.piercingPower)
                    shellInfo['speed'] = round(shot.speed/0.8, 3)
                    shellInfo['gravity'] = round(shot.gravity/0.64, 3)
                    shellInfo['maxDistance'] = shot.maxDistance
                    if shot.shell.kind == 'HIGH_EXPLOSIVE':
                        shellInfo['explosionRadius'] = shot.shell.type.explosionRadius
                    break
            if shellInfo:
                eventInfo.append(json.dumps(shellInfo))
            printStrings(LOG_EVENTS_FILENAME, eventInfo)

    @g_overrideLib.registerEvent(Vehicle, 'showDamageFromShot')
    def new_showDamageFromShot(self, attackerID, points, effectsIndex, damageFactor, *a, **k):
        if LOG_EVENTS and attackerID > 0:
            player = BigWorld.player()
            #Initial info
            points_count = len(points) if points else 0
            timeLeft, timeLeftSec = getTimeLeft()
            eventInfo = ['%s' % player.arenaUniqueID, timeLeft, timeLeftSec,
                         '"Vehicle.showDamageFromShot"',
                         '%s' % player.arena.vehicles[self.id].get('accountDBID', '-'),
                         '%s' % player.arena.vehicles[attackerID].get('accountDBID', '-'),
                         json.dumps({'points':points_count, 'effectsIndex':effectsIndex, 'damageFactor':damageFactor})]
            #Decode info
            shellInfo = {}
            for shot in player.arena.vehicles[attackerID]['vehicleType'].gun.shots:
                if effectsIndex == shot.shell.effectsIndex:
                    shellInfo['name'] = shot.shell.name
                    shellInfo['kind'] = shellTypeAbb(shot.shell.kind)
                    shellInfo['damage'] = str(shot.shell.damage)
                    shellInfo['caliber'] = shot.shell.caliber
                    shellInfo['piercingPower'] = str(shot.piercingPower)
                    shellInfo['speed'] = round(shot.speed/0.8, 3)
                    shellInfo['gravity'] = round(shot.gravity/0.64, 3)
                    shellInfo['maxDistance'] = shot.maxDistance
                    if shot.shell.kind == 'HIGH_EXPLOSIVE':
                        shellInfo['explosionRadius'] = shot.shell.type.explosionRadius
                    break
            eventInfo.append(json.dumps(shellInfo) if shellInfo else '')
            maxHitEffectCode, decodedPoints, maxDamagedComponent = DamageFromShotDecoder.decodeHitPoints(points, self.appearance.collisions)
            hasPiercedHit = DamageFromShotDecoder.hasDamaged(maxHitEffectCode)
            attacker = BigWorld.entities.get(attackerID, None)
            attackerPos = attacker.position if isinstance(attacker, Vehicle) and attacker.inWorld and attacker.isStarted else player.arena.positions.get(attackerID)
            eventInfo.append(json.dumps({'maxHitEffectCode': VEHICLE_HIT_EFFECT_NAMES.get(maxHitEffectCode), 'maxDamagedComponent': maxDamagedComponent,
                                         'hasPiercedHit': hasPiercedHit, 'distance': round(self.position.distTo(attackerPos), 3) if attackerPos else None,
                                         'hitPoints': [{'componentName': point.componentName, 'hitEffectGroup': point.hitEffectGroup} for point in decodedPoints] if decodedPoints else None}))
            for num, encodedPoint in enumerate(points, 1):
                hitsInfo = [] #[[Dir1-Layer1, ...], [Dir2-Layer1, ...], ...]
                hitsScheme = None
                compIdx, hitEffectCode, startPoint, endPoint = DamageFromShotDecoder.decodeSegment(encodedPoint, self.appearance.collisions, TankPartIndexes.ALL[-1])
                if compIdx >= 0 and startPoint != endPoint: 
                    convertedCompIdx = DamageFromShotDecoder.convertComponentIndex(compIdx)
                    bbox = self.appearance.collisions.getBoundingBox(convertedCompIdx)
                    width, height, depth = (bbox[1] - bbox[0]) / 256.0
                    if COLLIDE_MULTI:
                        if COLLIDE_SCHEME == 'hexahedron':
                            hitsScheme = _CSHexahedron(width, height, depth, COLLIDE_SCALE)
                        elif COLLIDE_SCHEME == 'cross':
                            hitsScheme = _CSCross(width, height, depth, COLLIDE_SCALE)
                        else:
                            hitsScheme = _CSCenter()
                    else:
                        hitsScheme = _CSCenter()
                    compMatrix = Matrix(self.appearance.compoundModel.node(TankPartIndexes.getName(convertedCompIdx)))
                    firstHitDir = endPoint - startPoint
                    firstHitDir.normalise()
                    firstHitDir = compMatrix.applyVector(firstHitDir)
                    firstHitPos = compMatrix.applyPoint(startPoint)
                    for direction in hitsScheme.directions:
                        hitInfo = []
                        collisions = self.appearance.collisions.collideAllWorld(firstHitPos - firstHitDir.scale(COLLIDE_INDENT) + direction, firstHitPos + firstHitDir.scale(COLLIDE_LENGTH) + direction)
                        if collisions:
                            base = None
                            testPointAdded = collidePointAdded = False
                            for collision in collisions:
                                if collision[3] in TankPartIndexes.ALL:
                                    if base is None:
                                        base = collision[0] 
                                    if not testPointAdded:
                                        if collision[0] > COLLIDE_INDENT:
                                            hitInfo.append('TestPoint%s(distance=%s, tankPart=%s)' % (num if points_count > 1 else '', round(COLLIDE_INDENT - base, 4), TankPartIndexes.getName(convertedCompIdx)))
                                            testPointAdded = True
                                    material = self.getMatinfo(collision[3], collision[2])
                                    hitInfo.append({'distance': round(collision[0] - base, 4), 'angleCos': round(collision[1], 4), 'tankPart': TankPartIndexes.getName(collision[3]),
                                                    'armor': round(material.armor, 4) if material else None})
                                    if not collidePointAdded:
                                        collidePointAdded = True
                                    if material and material.vehicleDamageFactor > 0 and collision[3] in (TankPartIndexes.HULL, TankPartIndexes.TURRET):
                                        break
                            if collidePointAdded:
                                if not testPointAdded and base is not None:
                                    hitInfo.append('TestPoint%s(distance=%s, tankPart=%s)' % (num if points_count > 1 else '', round(COLLIDE_INDENT - base, 4), TankPartIndexes.getName(convertedCompIdx)))
                        hitsInfo.append(hitInfo)
                eventInfo.append(json.dumps('%s: %s' % ('TestPoint%d' % num if points_count > 1 else 'layers' if hitsScheme.NAME == 'center' else 'TestPoint', \
                                                        hitsScheme.format(hitsInfo[0] if hitsScheme.NAME == 'center' else hitsInfo) if hitsScheme else '[]')))
            printStrings(LOG_EVENTS_FILENAME, eventInfo)

    @g_overrideLib.registerEvent(Vehicle, 'showDamageFromExplosion')
    def new_showDamageFromExplosion(self, attackerID, center, effectsIndex, damageFactor, *a, **k):
        if LOG_EVENTS and attackerID > 0:
            player = BigWorld.player()
            #Initial info
            timeLeft, timeLeftSec = getTimeLeft()
            eventInfo = ['%s' % player.arenaUniqueID, timeLeft, timeLeftSec,
                         '"Vehicle.showDamageFromExplosion"',
                         '%s' % player.arena.vehicles[self.id].get('accountDBID', '-'),
                         '%s' % player.arena.vehicles[attackerID].get('accountDBID', '-'),
                         json.dumps({'effectsIndex':effectsIndex, 'damageFactor':damageFactor})]
            #Decode info
            shellInfo = {}
            for shot in player.arena.vehicles[attackerID]['vehicleType'].gun.shots:
                if effectsIndex == shot.shell.effectsIndex:
                    shellInfo['name'] = shot.shell.name
                    shellInfo['kind'] = shellTypeAbb(shot.shell.kind)
                    shellInfo['damage'] = str(shot.shell.damage)
                    shellInfo['caliber'] = shot.shell.caliber
                    shellInfo['piercingPower'] = str(shot.piercingPower)
                    shellInfo['speed'] = round(shot.speed/0.8, 3)
                    shellInfo['gravity'] = round(shot.gravity/0.64, 3)
                    shellInfo['maxDistance'] = shot.maxDistance
                    if shot.shell.kind == 'HIGH_EXPLOSIVE':
                        shellInfo['explosionRadius'] = shot.shell.type.explosionRadius
                    break
            eventInfo.append(json.dumps(shellInfo) if shellInfo else '')
            eventInfo.append(json.dumps({'distance': self.position.distTo(center)}))
            printStrings(LOG_EVENTS_FILENAME, eventInfo)

    print '[%s] Loading mod: "simple_logger" %s (http://www.koreanrandom.com)' % (__author__, __version__)