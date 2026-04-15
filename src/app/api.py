import os
import base64
import urllib.parse
import re
import json
import threading
from pathlib import Path
from src.udp.telemetry_UDP import F1TelemetryServer
from src.app.tools import TrackTranslator, SessionTypeTranslator, WeatherTranslator

from analisys.GroupData import F125_TelemetryConsolidated
from analisys.John import John
from analisys.Mary import Mary

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
        
        self.parquet_json_path = "analisys/sanitazed_data/"
        
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
    
    def hasTrainingData(self, track, session) -> bool:        
        track_training = {}
        with open(f"analisys/sanitazed_data/summary.jsonl", "r") as f:
            for row in f:
                row_data = json.loads(row)                
                if (row_data['track'] == track and row_data['session'] == session):
                    return True
                
        return False
    
    def counterTrackTrainingSessions(self, track):
        counter = 0
        with open(f"analisys/sanitazed_data/summary.jsonl", "r") as f:
            for row in f:
                row_data = json.loads(row)
                if (row_data['track'] == track):
                    counter += 1
                    
        return counter
    
    def getSessionData(self, session, track):
        with open(f"laps/{track}/{session}/session.jsonl", "r", encoding='utf-8') as f:
            last_line = f.readlines()[-1]
            aux = json.loads(last_line)
            
        with open(f"laps/{track}/{session}/participants.jsonl", "r", encoding='utf-8') as f:
            last_line_participants = f.readlines()[-1]
            aux_participants = json.loads(last_line_participants)
            
        return {
            "session_id": session,
            "is_trained": self.hasTrainingData(track, session),
            "pilot_name": aux_participants['data']['name'],
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
                    "trained_sessions": self.counterTrackTrainingSessions(f"Track_{matches[0]}"),
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
    
    def getSessionParquet(self, data):
        group_data = F125_TelemetryConsolidated(track=data['track'], session=data['session'])
                
        return group_data.getBasicConsolidated()
    
    def setModelTraining(self, track, session):        
        try:
            john = John(track=track, session=session, num_laps=3)
            return john.runAll()
        except Exception as e:
            raise RuntimeError(e)
        
    def makeLapAnalisys(self, track, session_training, session_analisys, selected_lap):
        try:
            mary = Mary(track=track, session_training=session_training, session_analisys=session_analisys, lap_to_analize=int(selected_lap))
            return mary.runAll()
        except Exception as e:
            raise RuntimeError(e)
    
    def getSanitazeSummary(self):        
        data = []
        with open(f"analisys/sanitazed_data/summary.jsonl", 'r', encoding='utf-8') as file:
            for line in file:
                row = json.loads(line)
                data.append({
                    "track": {"id": row['track'], "label": self.track_translator.translate(int(row['track'].replace("Track_", "")))},
                    "session": self.getSessionData(row['session'], row['track']),
                    "sanitaze_summary": row
                })
                
        return data
    
    def getTrackTrainings(self, track):
        data = []
        with open(f"analisys/sanitazed_data/summary.jsonl", "r", encoding="utf-8") as f:
            for row in f:
                row_data = json.loads(row)
                
                data.append({
                    "track": row_data['track'],
                    "track_label": self.track_translator.translate(int(row_data['track'].replace("Track_", ""))),
                    "session_id": row_data['session'],
                    "session": self.getSessionData(row_data['session'], row_data['track'])
                })
                
        return data
    
    def get_asset_path(self, relative_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, relative_path)
        return "file://" + urllib.parse.quote(full_path.replace("\\", "/")).replace("/src/app", "")
    
    def loadAnalisysData(self, track, session, lap):
        relative_path = f"analisys/models/{track}/{session}/{lap}"
        # data_path = self.get_asset_path(relative_path)
        
        txt_feedback = ""
        with open(f"{relative_path}/performance_feedback.txt", "r", encoding='utf-8') as file:
            txt_feedback = file.read()
            
        lap_comparison = ""
        with open(f"{relative_path}/lap_comparison.png", "rb") as f:
            lap_comparison = base64.b64encode(f.read()).decode("utf-8")
            
        lap_trace = ""
        with open(f"{relative_path}/lap_trace.png", "rb") as f1:
            lap_trace = base64.b64encode(f1.read()).decode("utf-8")
            
        performance_radar = ""
        with open(f"{relative_path}/performance_radar.png", "rb") as f2:
            performance_radar = base64.b64encode(f2.read()).decode("utf-8")
        
        return {
            "lap_comparison": lap_comparison,
            "lap_trace": lap_trace,
            "performance_radar": performance_radar,
            "performance_feedback": txt_feedback
        }
    
    
# api = Api()
# api.getLaps(13, '2236946438891290374') 