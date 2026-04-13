import time
import re
import json
import threading
from pathlib import Path
from src.udp.telemetry_UDP import F1TelemetryServer
from src.app.tools import TrackTranslator, SessionTypeTranslator, WeatherTranslator

class Telemetry:
    def __init__(self, lock):
        self.telemetry_server = None
        self.lock = lock
        self.running = True        
        
    def start_telemetry_server(self):
        self.telemetry_server = F1TelemetryServer()
        self.telemetry_server.run()
    
    def telemetry_thread(self):
        self.start_telemetry_server()

class Api:
    def __init__(self):
        self.telemetry_thread = None
        self.lock = threading.Lock()
        self.telemetry_class = Telemetry(lock=self.lock)
        self.track_translator = TrackTranslator()
        self.session_type_translator = SessionTypeTranslator()
        self.weather_translator = WeatherTranslator()
        
    def getTelemetryUdpStatus(self):
        if self.telemetry_thread and self.telemetry_thread.is_alive():            
            return True
        return False
    
    def startTelemetryUDP(self):
        self.telemetry_thread = threading.Thread(target=self.telemetry_class.telemetry_thread)        
        self.telemetry_thread.start()
        
    def stopTelemetryUDP(self):
        if self.telemetry_thread and self.telemetry_thread.is_alive():
            self.telemetry_thread.join()                
    
    def getModule(self, module:str, file:str = 'index.html'):
        with open(f"views/modules/{module}/{file}", "r", encoding="utf-8") as file:
            return file.read()        
        
    def getLaps(self, track, session):
        path = Path(f"laps/Track_{track}/{session}")
        laps_path = [p.name for p in path.iterdir() if p.is_dir()]
        
        return {
            "track": f"Track_{track}",
            "session": session,
            "laps": laps_path
        }
    
    def getLapData(self, lap, session, track):
        lap_data = {}
        with open(f"laps/{track}/{session}/{lap}/lap_status.jsonl", 'r', encoding='utf-8') as f:
            last_line = f.readlines()[-1]
            aux = json.loads(last_line)
            lap_data = {
                "currentLapTimeInMS": aux['data']['currentLapTimeInMS'],
                "currentLapNum": aux['data']['currentLapNum']
            }
            
        return lap_data
    
    def getSessionData(self, session, track):
        with open(f"laps/{track}/{session}/session.jsonl", "r", encoding='utf-8') as f:
            last_line = f.readlines()[-1]
            aux = json.loads(last_line)
            
        return {
            "session_id": session,
            "datetime": aux['data']['datetime'], 
            "total_laps": aux['data']['totalLaps'],
            "sessionType": self.session_type_translator.translate(aux['data']['sessionType']),
            "airTemperature": aux['data']['airTemperature'],
            "trackTemperature": aux['data']['trackTemperature'],
            "weather": self.weather_translator.translate(aux['data']['weather'])
        }
        
    def getLapHistory(self):
        laps = {}
        with open(f"laps/lap_history.jsonl", "r", encoding="utf-8") as f:
            for l in f:
                row = json.loads(l)
                
                track_id = f"Track_{row['track']}"
                session_id = f"{row['session']}"
                lap = f"Lap_{row['lap']}"
                
                if track_id not in laps:
                    laps[track_id] = {}
                    
                if session_id not in laps[track_id]:
                    laps[track_id][session_id] = []
                    
                laps[track_id][session_id].append(lap)
                
        _tracks = []        
        for item in laps:
            session_laps = []
            for session in laps[item]:                          
                _session = self.getSessionData(session, item)                
                _session['laps'] = [self.getLapData(x, session, item) for x in laps[item][session]]
                session_laps.append(_session)                           
                
            matches = re.findall(r'\d+', item)
            if matches:
                _tracks.append({
                    "track_id": int(matches[0]),
                    "track_label": self.track_translator.translate(int(matches[0])),
                    "sessions": session_laps
                })                        
        
                
        return _tracks
    
    def getTracks(self):
        path = Path(f"laps/")
        tracks_path = [p.name for p in path.iterdir() if p.is_dir()]
        
        tracks = []
        for track in tracks_path:
            tracks.append({
                "track_id": track,
                "track_label": self.track_translator.translate(int(track.replace("Track_", "")))
            })
            
        
        return tracks
    
    def getTrackSummary(self, track:str):
        sessions = Path(f"laps/{track}")
        sessions = [p.name for p in sessions.iterdir() if p.is_dir()]
        
        return [self.getSessionData(session, track) for session in sessions]
    
    def setModelTraining(self):
        time.sleep(2)
        # Aplicar algoritimo de treinamento do ML aqui e salvar caminho dos arquivos em um json na mesma pasta dos arquivos do treinamento e sanitizados
        return "Concluído"
    
    
# api = Api()
# api.getLaps(13, '2236946438891290374')