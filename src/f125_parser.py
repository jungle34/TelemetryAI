"""
F1 25 UDP Telemetry Parser
Classe para parsear e acessar dados de telemetria do F1 25 Game via UDP
Formato dos dados: Little Endian, packed structures
"""

import struct
from typing import Dict, Any, List, Union
from enum import IntEnum


class PacketType(IntEnum):
    """IDs dos tipos de pacotes"""
    MOTION = 0
    SESSION = 1
    LAP_DATA = 2
    EVENT = 3
    PARTICIPANTS = 4
    CAR_SETUPS = 5
    CAR_TELEMETRY = 6
    CAR_STATUS = 7
    FINAL_CLASSIFICATION = 8
    LOBBY_INFO = 9
    CAR_DAMAGE = 10
    SESSION_HISTORY = 11
    TYRE_SETS = 12
    MOTION_EX = 13
    TIME_TRIAL = 14
    LAP_POSITIONS = 15


class F1TelemetryParser:
    """
    Parser para dados de telemetria UDP do F1 25 Game
    
    Uso:
        parser = F1TelemetryParser()
        data = parser.parse(udp_packet_bytes)
        
        # Acessar dados via dict
        print(data['header']['sessionUID'])
        print(data['carMotionData'][0]['worldPositionX'])
    """
    
    def __init__(self):
        self.packet_format = 2025
        
    def parse(self, packet: bytes) -> Dict[str, Any]:
        """
        Parseia um pacote UDP completo
        
        Args:
            packet: Bytes recebidos via UDP
            
        Returns:
            Dict com dados parseados, acessíveis por chave
        """
        # Parse header primeiro para identificar tipo de pacote
        header = self._parse_header(packet[:29])
        
        # Verifica formato do pacote
        if header['packetFormat'] != self.packet_format:
            raise ValueError(f"Formato de pacote inválido: {header['packetFormat']}, esperado: {self.packet_format}")
        
        # Parse baseado no tipo de pacote
        packet_id = header['packetId']
        
        parsers = {
            PacketType.MOTION: self._parse_motion,
            PacketType.SESSION: self._parse_session,
            PacketType.LAP_DATA: self._parse_lap_data,
            PacketType.EVENT: self._parse_event,
            PacketType.PARTICIPANTS: self._parse_participants,
            PacketType.CAR_SETUPS: self._parse_car_setups,
            PacketType.CAR_TELEMETRY: self._parse_car_telemetry,
            PacketType.CAR_STATUS: self._parse_car_status,
            PacketType.FINAL_CLASSIFICATION: self._parse_final_classification,
            PacketType.LOBBY_INFO: self._parse_lobby_info,
            PacketType.CAR_DAMAGE: self._parse_car_damage,
            PacketType.SESSION_HISTORY: self._parse_session_history,
            PacketType.TYRE_SETS: self._parse_tyre_sets,
            PacketType.MOTION_EX: self._parse_motion_ex,
            PacketType.TIME_TRIAL: self._parse_time_trial,
            PacketType.LAP_POSITIONS: self._parse_lap_positions,
        }
        
        if packet_id in parsers:
            result = parsers[packet_id](packet)
            result['header'] = header
            return result
        else:
            raise ValueError(f"Tipo de pacote desconhecido: {packet_id}")
    
    def _parse_header(self, data: bytes) -> Dict[str, Any]:
        """Parse PacketHeader (29 bytes)"""
        unpacked = struct.unpack('<HBBBBBQfIIBB', data)
        return {
            'packetFormat': unpacked[0],
            'gameYear': unpacked[1],
            'gameMajorVersion': unpacked[2],
            'gameMinorVersion': unpacked[3],
            'packetVersion': unpacked[4],
            'packetId': unpacked[5],
            'sessionUID': unpacked[6],
            'sessionTime': unpacked[7],
            'frameIdentifier': unpacked[8],
            'overallFrameIdentifier': unpacked[9],
            'playerCarIndex': unpacked[10],
            'secondaryPlayerCarIndex': unpacked[11],
        }
    
    def _parse_motion(self, packet: bytes) -> Dict[str, Any]:
        """Parse PacketMotionData (1349 bytes)"""
        offset = 29  # Após header
        car_motion_data = []
        
        # Parse dados de movimento para 22 carros
        for _ in range(22):
            car_data = struct.unpack('<ffffffhhhhhhffffff', packet[offset:offset+60])
            car_motion_data.append({
                'worldPositionX': car_data[0],
                'worldPositionY': car_data[1],
                'worldPositionZ': car_data[2],
                'worldVelocityX': car_data[3],
                'worldVelocityY': car_data[4],
                'worldVelocityZ': car_data[5],
                'worldForwardDirX': car_data[6] / 32767.0,  # Normalizado
                'worldForwardDirY': car_data[7] / 32767.0,
                'worldForwardDirZ': car_data[8] / 32767.0,
                'worldRightDirX': car_data[9] / 32767.0,
                'worldRightDirY': car_data[10] / 32767.0,
                'worldRightDirZ': car_data[11] / 32767.0,
                'gForceLateral': car_data[12],
                'gForceLongitudinal': car_data[13],
                'gForceVertical': car_data[14],
                'yaw': car_data[15],
                'pitch': car_data[16],
                'roll': car_data[17],
            })
            offset += 60
        
        return {'carMotionData': car_motion_data}
    
    def _parse_session(self, packet: bytes) -> Dict[str, Any]:
        """Parse PacketSessionData (753 bytes)"""
        offset = 29
        
        # Parse dados principais da sessão
        session_data = struct.unpack('<BbbBHBbBHHBBBBB', packet[offset:offset+18])
        offset += 18
        
        # Parse marshal zones (21 zonas)
        marshal_zones = []
        for _ in range(18):
            zone = struct.unpack('<fb', packet[offset:offset+5])
            marshal_zones.append({
                'zoneStart': zone[0],
                'zoneFlag': zone[1]
            })
            offset += 5
        
        # Parse status safety car e network
        safety_network = struct.unpack('<BB', packet[offset:offset+2])
        offset += 2
        
        # Parse weather forecast samples (64 amostras)
        weather_samples = []
        num_samples = struct.unpack('<B', packet[offset:offset+1])[0]
        offset += 1
        
        for _ in range(64):
            sample = struct.unpack('<BBBbbbbB', packet[offset:offset+8])
            weather_samples.append({
                'sessionType': sample[0],
                'timeOffset': sample[1],
                'weather': sample[2],
                'trackTemperature': sample[3],
                'trackTemperatureChange': sample[4],
                'airTemperature': sample[5],
                'airTemperatureChange': sample[6],
                'rainPercentage': sample[7],
            })
            offset += 8
        
        # Parse resto dos dados
        remaining = struct.unpack('<BIIIIBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBIBBBBBff', packet[offset:offset+64])
        
        return {
            'weather': session_data[0],
            'trackTemperature': session_data[1],
            'airTemperature': session_data[2],
            'totalLaps': session_data[3],
            'trackLength': session_data[4],
            'sessionType': session_data[5],
            'trackId': session_data[6],
            'formula': session_data[7],
            'sessionTimeLeft': session_data[8],
            'sessionDuration': session_data[9],
            'pitSpeedLimit': session_data[10],
            'gamePaused': session_data[11],
            'isSpectating': session_data[12],
            'spectatorCarIndex': session_data[13],
            'sliProNativeSupport': session_data[14],
            'numMarshalZones': session_data[14],
            'marshalZones': marshal_zones,
            'safetyCarStatus': safety_network[0],
            'networkGame': safety_network[1],
            'numWeatherForecastSamples': num_samples,
            'weatherForecastSamples': weather_samples[:num_samples],
            'forecastAccuracy': remaining[0],
            'aiDifficulty': remaining[1],
            'seasonLinkIdentifier': remaining[2],
            'weekendLinkIdentifier': remaining[3],
            'sessionLinkIdentifier': remaining[4],
            'pitStopWindowIdealLap': remaining[5],
            'pitStopWindowLatestLap': remaining[6],
            'pitStopRejoinPosition': remaining[7],
            'sector2LapDistanceStart': remaining[-2],
            'sector3LapDistanceStart': remaining[-1],
        }
    
    def _parse_lap_data(self, packet: bytes):
        offset = 29
        lap_data = []

        fmt = '<IIHBHBHBHBfff15BHHBfB'
        size = struct.calcsize(fmt)

        for _ in range(22):
            data = struct.unpack_from(fmt, packet, offset)

            lap_data.append({
                'lastLapTimeInMS': data[0],
                'currentLapTimeInMS': data[1],
                'sector1TimeMSPart': data[2],
                'sector1TimeMinutesPart': data[3],
                'sector2TimeMSPart': data[4],
                'sector2TimeMinutesPart': data[5],
                'deltaToCarInFrontMSPart': data[6],
                'deltaToCarInFrontMinutesPart': data[7],
                'deltaToRaceLeaderMSPart': data[8],
                'deltaToRaceLeaderMinutesPart': data[9],

                'lapDistance': data[10],
                'totalDistance': data[11],
                'safetyCarDelta': data[12],

                'carPosition': data[13],
                'currentLapNum': data[14],
                'pitStatus': data[15],
                'numPitStops': data[16],
                'sector': data[17],
                'currentLapInvalid': data[18],
                'penalties': data[19],
                'totalWarnings': data[20],
                'cornerCuttingWarnings': data[21],
                'numUnservedDriveThroughPens': data[22],
                'numUnservedStopGoPens': data[23],
                'gridPosition': data[24],
                'driverStatus': data[25],
                'resultStatus': data[26],
                'pitLaneTimerActive': data[27],

                'pitLaneTimeInLaneInMS': data[28],
                'pitStopTimerInMS': data[29],

                'pitStopShouldServePen': data[30],
                'speedTrapFastestSpeed': data[31],
                'speedTrapFastestLap': data[32],
            })

            offset += size

        tt_indices = struct.unpack_from('<BB', packet, offset)

        return {
            'lapData': lap_data,
            'timeTrialPBCarIdx': tt_indices[0],
            'timeTrialRivalCarIdx': tt_indices[1],
        }
    
    def _parse_event(self, packet: bytes) -> Dict[str, Any]:
        """Parse PacketEventData (45 bytes)"""
        offset = 29
        
        # Event string code (4 chars)
        event_code = packet[offset:offset+4].decode('utf-8', errors='ignore')
        offset += 4
        
        # Event details variam baseado no código
        # Parse básico para os dados do evento (union de 12 bytes máximo)
        event_data = packet[offset:offset+12]
        
        result = {
            'eventStringCode': event_code,
            'eventDataRaw': event_data,
        }
        
        # Parse específico baseado no código do evento
        if event_code == 'FTLP':  # Fastest Lap
            details = struct.unpack('<Bf', event_data[:5])
            result['vehicleIdx'] = details[0]
            result['lapTime'] = details[1]
        elif event_code == 'RTMT':  # Retirement
            details = struct.unpack('<BB', event_data[:2])
            result['vehicleIdx'] = details[0]
            result['reason'] = details[1]
        elif event_code == 'PENA':  # Penalty
            details = struct.unpack('<BBBBBBB', event_data[:7])
            result['penaltyType'] = details[0]
            result['infringementType'] = details[1]
            result['vehicleIdx'] = details[2]
            result['otherVehicleIdx'] = details[3]
            result['time'] = details[4]
            result['lapNum'] = details[5]
            result['placesGained'] = details[6]
        elif event_code == 'SPTP':  # Speed Trap
            details = struct.unpack('<BfBBBf', event_data[:12])
            result['vehicleIdx'] = details[0]
            result['speed'] = details[1]
            result['isOverallFastestInSession'] = details[2]
            result['isDriverFastestInSession'] = details[3]
            result['fastestVehicleIdxInSession'] = details[4]
            result['fastestSpeedInSession'] = details[5]
        
        return result
    
    def _parse_participants(self, packet: bytes):
        offset = 29
        
        num_active_cars = struct.unpack('<B', packet[offset:offset+1])[0]
        offset += 1
        
        participants = []

        for _ in range(22):            
            data = struct.unpack('<BBBBBBB32sBBHBB', packet[offset:offset+45])
            offset += 45
            
            livery_colours = []
            for _ in range(4):
                rgb = struct.unpack('<BBB', packet[offset:offset+3])
                livery_colours.append({
                    'red': rgb[0],
                    'green': rgb[1],
                    'blue': rgb[2]
                })
                offset += 3
            
            name = data[7].rstrip(b'\x00').decode('utf-8')            

            participants.append({
                'aiControlled': data[0],
                'driverId': data[1],
                'networkId': data[2],
                'teamId': data[3],
                'myTeam': data[4],
                'raceNumber': data[5],
                'nationality': data[6],
                'name': name,
                'yourTelemetry': data[8],
                'showOnlineNames': data[9],
                'techLevel': data[10],
                'platform': data[11],
                'numColours': data[12],
                'liveryColours': livery_colours,
            })

        return {
            'numActiveCars': num_active_cars,
            'participants': participants,
        }
    
    def _parse_car_setups(self, packet: bytes) -> Dict[str, Any]:
        """Parse PacketCarSetupData (1133 bytes)"""
        offset = 29
        car_setups = []
        
        for _ in range(22):
            data = struct.unpack('<BBBBffffBBBBBBBBffffBf', packet[offset:offset+49])
            car_setups.append({
                'frontWing': data[0],
                'rearWing': data[1],
                'onThrottle': data[2],
                'offThrottle': data[3],
                'frontCamber': data[4],
                'rearCamber': data[5],
                'frontToe': data[6],
                'rearToe': data[7],
                'frontSuspension': data[8],
                'rearSuspension': data[9],
                'frontAntiRollBar': data[10],
                'rearAntiRollBar': data[11],
                'frontSuspensionHeight': data[12],
                'rearSuspensionHeight': data[13],
                'brakePressure': data[14],
                'brakeBias': data[15],
                'engineBraking': data[16],
                'rearLeftTyrePressure': data[17],
                'rearRightTyrePressure': data[18],
                'frontLeftTyrePressure': data[19],
                'frontRightTyrePressure': data[20],
                'ballast': data[21],
                'fuelLoad': data[21],
            })
            offset += 49
        
        next_front_wing = struct.unpack('<f', packet[offset:offset+4])[0]
        
        return {
            'carSetups': car_setups,
            'nextFrontWingValue': next_front_wing,
        }
    
    def _parse_car_telemetry(self, packet: bytes):
        offset = 29
        car_telemetry = []

        fmt = '<HfffBbHBBH4H4B4BH4f4B'
        size = struct.calcsize(fmt)

        for _ in range(22):
            data = struct.unpack_from(fmt, packet, offset)

            car_telemetry.append({
                'speed': data[0],
                'throttle': data[1],
                'steer': data[2],
                'brake': data[3],
                'clutch': data[4],
                'gear': data[5],
                'engineRPM': data[6],
                'drs': data[7],
                'revLightsPercent': data[8],
                'revLightsBitValue': data[9],
                'brakesTemperature': list(data[10:14]),
                'tyresSurfaceTemperature': list(data[14:18]),
                'tyresInnerTemperature': list(data[18:22]),
                'engineTemperature': data[22],
                'tyresPressure': list(data[23:27]),
                'surfaceType': list(data[27:31]),
            })

            offset += size

        mfd_data = struct.unpack_from('<BBb', packet, offset)

        return {
            'carTelemetryData': car_telemetry,
            'mfdPanelIndex': mfd_data[0],
            'mfdPanelIndexSecondaryPlayer': mfd_data[1],
            'suggestedGear': mfd_data[2],
        }
    
    def _parse_car_status(self, packet: bytes) -> Dict[str, Any]:
        """Parse PacketCarStatusData (1239 bytes)"""
        offset = 29  # Tamanho do PacketHeader
        car_status = []
        struct_fmt = '<BBBBBfffHHBBHBBBbfffBfffB'
        struct_size = struct.calcsize(struct_fmt)  # 55 bytes

        for _ in range(22):  # 22 carros conforme especificação
            chunk = packet[offset:offset+struct_size]
            if len(chunk) != struct_size:
                # Pacote incompleto – pode lançar exceção ou ignorar
                break
            data = struct.unpack(struct_fmt, chunk)
            car_status.append({
                'tractionControl': data[0],
                'antiLockBrakes': data[1],
                'fuelMix': data[2],
                'frontBrakeBias': data[3],
                'pitLimiterStatus': data[4],
                'fuelInTank': data[5],
                'fuelCapacity': data[6],
                'fuelRemainingLaps': data[7],
                'maxRPM': data[8],
                'idleRPM': data[9],
                'maxGears': data[10],
                'drsAllowed': data[11],
                'drsActivationDistance': data[12],
                'actualTyreCompound': data[13],
                'visualTyreCompound': data[14],
                'tyresAgeLaps': data[15],
                'vehicleFiaFlags': data[16],
                'enginePowerICE': data[17],
                'enginePowerMGUK': data[18],
                'ersStoreEnergy': data[19],
                'ersDeployMode': data[20],
                'ersHarvestedThisLapMGUK': data[21],
                'ersHarvestedThisLapMGUH': data[22],
                'ersDeployedThisLap': data[23],
                'networkPaused': data[24],
            })
            offset += struct_size

        return {'carStatusData': car_status}
    
    def _parse_final_classification(self, packet: bytes) -> Dict[str, Any]:
        """Parse PacketFinalClassificationData (1042 bytes)"""
        offset = 29
        
        num_cars = struct.unpack('<B', packet[offset:offset+1])[0]
        offset += 1
        
        classifications = []
        for _ in range(22):
            data = struct.unpack('<BBBBBBBIdBBB8B8B8B', packet[offset:offset+45])
            classifications.append({
                'position': data[0],
                'numLaps': data[1],
                'gridPosition': data[2],
                'points': data[3],
                'numPitStops': data[4],
                'resultStatus': data[5],
                'resultReason': data[6],
                'bestLapTimeInMS': data[7],
                'totalRaceTime': data[8],
                'penaltiesTime': data[9],
                'numPenalties': data[10],
                'numTyreStints': data[11],
                'tyreStintsActual': list(data[12:20]),
                'tyreStintsVisual': list(data[20:28]),
                'tyreStintsEndLaps': list(data[28:36]),
            })
            offset += 45
        
        return {
            'numCars': num_cars,
            'classificationData': classifications,
        }
    
    def _parse_lobby_info(self, packet: bytes) -> Dict[str, Any]:
        """Parse PacketLobbyInfoData (954 bytes)"""
        offset = 29
        
        num_players = struct.unpack('<B', packet[offset:offset+1])[0]
        offset += 1
        
        lobby_players = []
        for _ in range(22):
            data = struct.unpack('<BBBb32sBBBHB', packet[offset:offset+43])
            lobby_players.append({
                'aiControlled': data[0],
                'teamId': data[1],
                'nationality': data[2],
                'platform': data[3],
                'name': data[4].decode('utf-8', errors='ignore').rstrip('\x00'),
                'carNumber': data[5],
                'yourTelemetry': data[6],
                'showOnlineNames': data[7],
                'techLevel': data[8],
                'readyStatus': data[9],
            })
            offset += 43
        
        return {
            'numPlayers': num_players,
            'lobbyPlayers': lobby_players,
        }
    
    def _parse_car_damage(self, packet: bytes) -> Dict[str, Any]:
        offset = 29
        car_damage = []

        fmt = '<4f4B4B4B18B'
        size = struct.calcsize(fmt)

        for i in range(22):
            chunk = packet[offset:offset + size]

            if len(chunk) != size:
                print(f"Erro no carro {i}: chunk inválido ({len(chunk)} bytes)")
                break

            data = struct.unpack(fmt, chunk)

            car_damage.append({
                'tyresWear': list(data[0:4]),
                'tyresDamage': list(data[4:8]),
                'brakesDamage': list(data[8:12]),
                'tyreBlisters': list(data[12:16]),

                'frontLeftWingDamage': data[16],
                'frontRightWingDamage': data[17],
                'rearWingDamage': data[18],
                'floorDamage': data[19],
                'diffuserDamage': data[20],
                'sidepodDamage': data[21],
                'drsFault': data[22],
                'ersFault': data[23],
                'gearBoxDamage': data[24],
                'engineDamage': data[25],
                'engineMGUHWear': data[26],
                'engineESWear': data[27],
                'engineCEWear': data[28],
                'engineICEWear': data[29],
                'engineMGUKWear': data[30],
                'engineTCWear': data[31],
                'engineBlown': data[32],
                'engineSeized': data[33],
            })

            offset += size

        return {'carDamageData': car_damage}

    def _parse_session_history(self, packet: bytes) -> Dict[str, Any]:
        """Parse PacketSessionHistoryData (1460 bytes)"""
        offset = 29
        
        # Parse índices e números
        indices = struct.unpack('<BBBBBBB', packet[offset:offset+7])
        offset += 7
        
        # Parse histórico de voltas (100 voltas)
        lap_history = []
        for _ in range(100):
            data = struct.unpack('<IHBHBHBB', packet[offset:offset+14])
            lap_history.append({
                'lapTimeInMS': data[0],
                'sector1TimeMSPart': data[1],
                'sector1TimeMinutesPart': data[2],
                'sector2TimeMSPart': data[3],
                'sector2TimeMinutesPart': data[4],
                'sector3TimeMSPart': data[5],
                'sector3TimeMinutesPart': data[6],
                'lapValidBitFlags': data[7],
            })
            offset += 14
        
        # Parse histórico de stints de pneus (8 stints)
        tyre_stints = []
        for _ in range(8):
            data = struct.unpack('<BBB', packet[offset:offset+3])
            tyre_stints.append({
                'endLap': data[0],
                'tyreActualCompound': data[1],
                'tyreVisualCompound': data[2],
            })
            offset += 3
        
        return {
            'carIdx': indices[0],
            'numLaps': indices[1],
            'numTyreStints': indices[2],
            'bestLapTimeLapNum': indices[3],
            'bestSector1LapNum': indices[4],
            'bestSector2LapNum': indices[5],
            'bestSector3LapNum': indices[6],
            'lapHistoryData': lap_history,
            'tyreStintsHistoryData': tyre_stints,
        }
    
    def _parse_tyre_sets(self, packet: bytes) -> Dict[str, Any]:
        """Parse PacketTyreSetsData (231 bytes)"""
        offset = 29
        
        car_idx = struct.unpack('<B', packet[offset:offset+1])[0]
        offset += 1
        
        # Parse 20 conjuntos de pneus (13 slick + 7 wet)
        tyre_sets = []
        for _ in range(20):
            data = struct.unpack('<BBBBBBBhB', packet[offset:offset+10])
            tyre_sets.append({
                'actualTyreCompound': data[0],
                'visualTyreCompound': data[1],
                'wear': data[2],
                'available': data[3],
                'recommendedSession': data[4],
                'lifeSpan': data[5],
                'usableLife': data[6],
                'lapDeltaTime': data[7],
                'fitted': data[8],
            })
            offset += 10
        
        fitted_idx = struct.unpack('<B', packet[offset:offset+1])[0]
        
        return {
            'carIdx': car_idx,
            'tyreSetData': tyre_sets,
            'fittedIdx': fitted_idx,
        }
    
    def _parse_motion_ex(self, packet: bytes) -> Dict[str, Any]:
        """Parse PacketMotionExData (273 bytes)"""
        offset = 29
        
        # Parse todos os arrays de 4 rodas e dados adicionais
        data = struct.unpack('<' + 'f'*4*11 + 'f'*9, packet[offset:offset+212])
        
        return {
            'suspensionPosition': list(data[0:4]),
            'suspensionVelocity': list(data[4:8]),
            'suspensionAcceleration': list(data[8:12]),
            'wheelSpeed': list(data[12:16]),
            'wheelSlipRatio': list(data[16:20]),
            'wheelSlipAngle': list(data[20:24]),
            'wheelLatForce': list(data[24:28]),
            'wheelLongForce': list(data[28:32]),
            'heightOfCOGAboveGround': data[32],
            'localVelocityX': data[33],
            'localVelocityY': data[34],
            'localVelocityZ': data[35],
            'angularVelocityX': data[36],
            'angularVelocityY': data[37],
            'angularVelocityZ': data[38],
            'angularAccelerationX': data[39],
            'angularAccelerationY': data[40],
            'angularAccelerationZ': data[41],
            'frontWheelsAngle': data[42],
            'wheelVertForce': list(data[43:47]),
            'frontAeroHeight': data[47],
            'rearAeroHeight': data[48],
            'frontRollAngle': data[49],
            'rearRollAngle': data[50],
            'chassisYaw': data[51],
            'chassisPitch': data[52],
            'wheelCamber': list(data[53:57]),
            'wheelCamberGain': list(data[57:61]),
        }
    
    def _parse_time_trial(self, packet: bytes) -> Dict[str, Any]:
        """Parse PacketTimeTrialData (101 bytes)"""
        offset = 29
        
        def parse_tt_dataset(data_bytes):
            data = struct.unpack('<BBIIIIBBBBB', data_bytes)
            return {
                'carIdx': data[0],
                'teamId': data[1],
                'lapTimeInMS': data[2],
                'sector1TimeInMS': data[3],
                'sector2TimeInMS': data[4],
                'sector3TimeInMS': data[5],
                'tractionControl': data[6],
                'gearboxAssist': data[7],
                'antiLockBrakes': data[8],
                'equalCarPerformance': data[9],
                'customSetup': data[10],
                'valid': data[11],
            }
        
        # Parse 3 datasets de 24 bytes cada
        player_best = parse_tt_dataset(packet[offset:offset+24])
        offset += 24
        personal_best = parse_tt_dataset(packet[offset:offset+24])
        offset += 24
        rival_data = parse_tt_dataset(packet[offset:offset+24])
        
        return {
            'playerSessionBestDataSet': player_best,
            'personalBestDataSet': personal_best,
            'rivalDataSet': rival_data,
        }
    
    def _parse_lap_positions(self, packet: bytes) -> Dict[str, Any]:
        """Parse PacketLapPositionsData (1131 bytes)"""
        offset = 29
        
        # Parse número de voltas e índice inicial
        header = struct.unpack('<BB', packet[offset:offset+2])
        offset += 2
        
        # Parse matriz de posições [50 voltas][22 carros]
        positions = []
        for lap in range(50):
            lap_positions = list(struct.unpack('<22B', packet[offset:offset+22]))
            positions.append(lap_positions)
            offset += 22
        
        return {
            'numLaps': header[0],
            'lapStart': header[1],
            'positionForVehicleIdx': positions,
        }


# # Exemplo de uso
# if __name__ == '__main__':
#     """
#     Exemplo de como usar o parser
#     """
#     import socket
    
#     # Configurar socket UDP
#     UDP_IP = "0.0.0.0"
#     UDP_PORT = 20777
    
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     sock.bind((UDP_IP, UDP_PORT))
    
#     parser = F1TelemetryParser()
    
#     print(f"Aguardando dados UDP em {UDP_IP}:{UDP_PORT}...")
    
#     while True:
#         data, addr = sock.recvfrom(2048)  # Buffer de 2048 bytes
        
#         try:
#             parsed = parser.parse(data)
            
#             # Exemplo de acesso aos dados via dict
#             print(f"\n{'='*60}")
#             print(f"Pacote ID: {parsed['header']['packetId']}")
#             print(f"Session UID: {parsed['header']['sessionUID']}")
#             print(f"Session Time: {parsed['header']['sessionTime']:.2f}s")
            
#             # Acesso específico baseado no tipo de pacote
#             if parsed['header']['packetId'] == PacketType.MOTION:
#                 player_idx = parsed['header']['playerCarIndex']
#                 player_data = parsed['carMotionData'][player_idx]
#                 print(f"\nPlayer Position: ({player_data['worldPositionX']:.2f}, "
#                       f"{player_data['worldPositionY']:.2f}, "
#                       f"{player_data['worldPositionZ']:.2f})")
#                 print(f"G-Forces: Lat={player_data['gForceLateral']:.2f}, "
#                       f"Long={player_data['gForceLongitudinal']:.2f}")
            
#             elif parsed['header']['packetId'] == PacketType.LAP_DATA:
#                 player_idx = parsed['header']['playerCarIndex']
#                 player_lap = parsed['lapData'][player_idx]
#                 print(f"\nCurrent Lap: {player_lap['currentLapNum']}")
#                 print(f"Position: {player_lap['carPosition']}")
#                 print(f"Lap Distance: {player_lap['lapDistance']:.2f}m")
            
#             elif parsed['header']['packetId'] == PacketType.CAR_TELEMETRY:
#                 player_idx = parsed['header']['playerCarIndex']
#                 player_tele = parsed['carTelemetryData'][player_idx]
#                 print(f"\nSpeed: {player_tele['speed']} km/h")
#                 print(f"Gear: {player_tele['gear']}")
#                 print(f"RPM: {player_tele['engineRPM']}")
#                 print(f"Throttle: {player_tele['throttle']:.1%}")
#                 print(f"Brake: {player_tele['brake']:.1%}")
            
#         except Exception as e:
#             print(f"Erro ao parsear pacote: {e}")
#             import traceback
#             traceback.print_exc()