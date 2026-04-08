import socket
from datetime import datetime
from src.udp.f125_parser import F1TelemetryParser
import json, os
import threading

class F1TelemetryServer:
    def __init__(self):
        self.parser = F1TelemetryParser()
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', 20777))  # F1 25 telemetry port
        self.sock.settimeout(1.0)
        self.track_id = -1
        
        self.packet_ids = [6, 2, 7, 0, 9, 1, 4, 10]
        self.current_lap_num = 0
        self.lock = threading.Lock()
        
        self.datetime_exec = datetime.now()
        
    def save_data(self, data: dict, file_path: str) -> None:
        with open(file_path, 'a') as f:
            f.write(json.dumps(data) + '\n')
            
    def save_live_data(self, data: dict) -> None:
        with self.lock:
            with open("live_data.json", 'r') as f:
                live_data = json.load(f)
                live_data.update(data)
                with open("live_data.json", 'w') as f:
                    json.dump(live_data, f, indent=4)
        
    def run(self):
        while True:
            try:
                data, _ = self.sock.recvfrom(4096)
                parsed_data = self.parser.parse(data)
                
                dict_to_save = {"type": "", "frame_id": 0, "data": {}}
                
                player_idx = parsed_data['header']['playerCarIndex']
                frame_identifier = parsed_data['header']['frameIdentifier']
                session_id = parsed_data['header']['sessionUID']
                
                if parsed_data['header']['packetId'] == 1:
                    self.track_id = parsed_data['trackId']
                    
                if self.track_id == -1:
                    continue
                
                if parsed_data['header']['packetId'] in self.packet_ids:
                    
                    if   parsed_data['header']['packetId'] == 6:
                        dict_to_save['type'] = "TELEMETRY"
                        dict_to_save['frame_id'] = frame_identifier
                        dict_to_save['data'] = parsed_data['carTelemetryData'][player_idx]                        
                        
                        os.makedirs(f"laps/Track_{self.track_id}/{session_id}/Lap_{lap_num}/", exist_ok=True)
                        self.save_data(dict_to_save, f"laps/Track_{self.track_id}/{session_id}/Lap_{lap_num}/telemtry.jsonl")
                        
                    elif parsed_data['header']['packetId'] == 2:
                        lap_num = parsed_data['lapData'][player_idx]['currentLapNum']
                        if lap_num != self.current_lap_num:
                            self.current_lap_num = lap_num
                            
                        dict_to_save['type'] = "LAP"
                        dict_to_save['frame_id'] = frame_identifier
                        dict_to_save['data'] = parsed_data['lapData'][player_idx]
                        os.makedirs(f"laps/Track_{self.track_id}/{session_id}/Lap_{lap_num}/", exist_ok=True)
                        self.save_data(dict_to_save, f"laps/Track_{self.track_id}/{session_id}/Lap_{lap_num}/lap_status.jsonl")
                            
                    elif parsed_data['header']['packetId'] == 7:
                        dict_to_save['type'] = "CAR_STATUS"
                        dict_to_save['frame_id'] = frame_identifier
                        dict_to_save['data'] = parsed_data['carStatusData'][player_idx]                                                

                        os.makedirs(f"laps/Track_{self.track_id}/{session_id}/Lap_{lap_num}/", exist_ok=True)
                        self.save_data(dict_to_save, f"laps/Track_{self.track_id}/{session_id}/Lap_{lap_num}/car_status.jsonl")

                    elif parsed_data['header']['packetId'] == 0:
                        dict_to_save['type'] = "MOTION_DATA"
                        dict_to_save['frame_id'] = frame_identifier
                        dict_to_save['data'] = parsed_data['carMotionData'][player_idx]

                        os.makedirs(f"laps/Track_{self.track_id}/{session_id}/Lap_{lap_num}/", exist_ok=True)
                        self.save_data(dict_to_save, f"laps/Track_{self.track_id}/{session_id}/Lap_{lap_num}/motion_data.jsonl")
                        
                    elif parsed_data['header']['packetId'] == 9:
                        dict_to_save['type'] = "LOBBY_INFO"
                        dict_to_save['frame_id'] = frame_identifier
                        dict_to_save['data'] = parsed_data['lobbyPlayers'][player_idx]
                        
                        os.makedirs(f"laps/Track_{self.track_id}/{session_id}/Lap_{lap_num}/", exist_ok=True)
                        self.save_data(dict_to_save, f"laps/Track_{self.track_id}/{session_id}/Lap_{lap_num}/lobby_info.jsonl")
                        
                    elif parsed_data['header']['packetId'] == 1:                        
                        aux = {
                            "weather": parsed_data['weather'],
                            "trackTemperature": parsed_data['trackTemperature'],
                            "airTemperature": parsed_data['airTemperature'],
                            "totalLaps": parsed_data['totalLaps'],
                            "sessionType": parsed_data['sessionType'],
                            "datetime": self.datetime_exec.strftime("%Y-%m-%d %H:%M:%S"),
                            "header": parsed_data['header']
                        }
                        
                        dict_to_save['type'] = "SESSION"
                        dict_to_save['frame_id'] = frame_identifier
                        dict_to_save['data'] = aux
                        
                        os.makedirs(f"laps/Track_{self.track_id}/{session_id}/", exist_ok=True)
                        self.save_data(dict_to_save, f"laps/Track_{self.track_id}/{session_id}/session.jsonl")
                        
                    elif parsed_data['header']['packetId'] == 4:
                        dict_to_save['type'] = "PARTICIPANTS"
                        dict_to_save['frame_id'] = frame_identifier
                        dict_to_save['data'] = parsed_data['participants'][player_idx]                    
                        
                        os.makedirs(f"laps/Track_{self.track_id}/{session_id}/", exist_ok=True)
                        self.save_data(dict_to_save, f"laps/Track_{self.track_id}/{session_id}/participants.jsonl")
                        
                    elif parsed_data['header']['packetId'] == 10:
                        dict_to_save['type'] = "CAR_DAMAGE"
                        dict_to_save['frame_id'] = frame_identifier
                        dict_to_save['data'] = parsed_data['carDamageData'][player_idx]
                        
                        os.makedirs(f"laps/Track_{self.track_id}/{session_id}/Lap_{lap_num}/", exist_ok=True)
                        self.save_data(dict_to_save, f"laps/Track_{self.track_id}/{session_id}/Lap_{lap_num}/car_damage.jsonl")
                                                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error: {e}")
                continue