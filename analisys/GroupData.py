import json
import re
import os
import pandas as pd
from pathlib import Path
from datetime import datetime

class F125_TelemetryConsolidated:
    def __init__(self, track, session, is_training:bool = True):
        self.session_id = session
        self.track = track
        self.is_training = is_training
        self.path = Path(f"laps/{self.track}/{self.session_id}")
        # pastas = [p for p in caminho.iterdir() if p.is_dir()]
        self.sanitazed_data = {}        
            
    def load_json_lines(self, json_path:str, lap:str) -> list:    
        with open(json_path, "r", encoding="utf-8") as f:
            for l in f:
                row = json.loads(l)
                frame_id = str(row['frame_id'])
                
                if lap not in self.sanitazed_data:
                    self.sanitazed_data[lap] = {}

                if frame_id not in self.sanitazed_data[lap]:
                    self.sanitazed_data[lap][frame_id] = {}
                                    
                try:
                    self.sanitazed_data[lap][frame_id][row['type']] = row['data']
                except:
                    print(row)
                    
    def loadBasicSanitizedData(self):
        for lap_path in [p for p in self.path.iterdir() if p.is_dir()]:
            self.load_json_lines(f"laps/{self.track}/{self.session_id}/{lap_path.name}/car_damage.jsonl", lap_path.name)
            self.load_json_lines(f"laps/{self.track}/{self.session_id}/{lap_path.name}/car_status.jsonl", lap_path.name)
            self.load_json_lines(f"laps/{self.track}/{self.session_id}/{lap_path.name}/lap_status.jsonl", lap_path.name)
            self.load_json_lines(f"laps/{self.track}/{self.session_id}/{lap_path.name}/motion_data.jsonl", lap_path.name)
            self.load_json_lines(f"laps/{self.track}/{self.session_id}/{lap_path.name}/telemtry.jsonl", lap_path.name)
            
    def saveParquet(self, data, output_path=f"telemetry_data/telemetry.parquet"):
        df = pd.DataFrame(data)
        
        df = df.convert_dtypes()    
        df.to_parquet(output_path, index=False)
        
    def save_data(self, data: dict, file_path: str) -> None:
        with open(file_path, 'a') as f:
            f.write(json.dumps(data) + '\n')
            
    def value_exists(self, file_path, key, target_value):
        if os.path.isfile(file_path):    
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if obj.get(key) == target_value:
                        return True

        return False
                            
    def getBasicConsolidated(self):
        if not self.value_exists("analisys/sanitazed_data/summary.jsonl", "session", self.session_id):
            self.loadBasicSanitizedData()
            consolidated = []
            for lap in self.sanitazed_data:            
                for i in self.sanitazed_data[lap]:
                    if all(chave in self.sanitazed_data[lap][i] for chave in ['TELEMETRY', 'LAP', 'CAR_STATUS', 'MOTION_DATA', 'CAR_DAMAGE']):                    
                        consolidated.append({
                            # LAP DATA
                            "lap": self.sanitazed_data[lap][i]['LAP']['currentLapNum'],
                            "pitStatus": self.sanitazed_data[lap][i]['LAP']['pitStatus'],
                            "lapDistance": self.sanitazed_data[lap][i]['LAP']['lapDistance'],
                            "sector": self.sanitazed_data[lap][i]['LAP']['sector'],
                            "currentLapTimeInMS": self.sanitazed_data[lap][i]['LAP']['currentLapTimeInMS'],
                            
                            # ENGINE & CONTROL TELEMETRY
                            "speed": self.sanitazed_data[lap][i]['TELEMETRY']['speed'],
                            "throttle": self.sanitazed_data[lap][i]['TELEMETRY']['throttle'],
                            "steer": self.sanitazed_data[lap][i]['TELEMETRY']['steer'],
                            "brake": self.sanitazed_data[lap][i]['TELEMETRY']['brake'],
                            "gear": self.sanitazed_data[lap][i]['TELEMETRY']['gear'],
                            "engineRPM": self.sanitazed_data[lap][i]['TELEMETRY']['engineRPM'],
                            "engineTemperature": self.sanitazed_data[lap][i]['TELEMETRY']['engineTemperature'],
                            "drs": self.sanitazed_data[lap][i]['TELEMETRY']['drs'],
                            "ersDeployMode": self.sanitazed_data[lap][i]['CAR_STATUS']['ersDeployMode'],
                            "actualTyreCompound": self.sanitazed_data[lap][i]['CAR_STATUS']['actualTyreCompound'],
                                        
                            # BRAKES TEMPERATURE
                            "brakesTemperatureFL": self.sanitazed_data[lap][i]['TELEMETRY']['brakesTemperature'][0],
                            "brakesTemperatureFR": self.sanitazed_data[lap][i]['TELEMETRY']['brakesTemperature'][1],
                            "brakesTemperatureRL": self.sanitazed_data[lap][i]['TELEMETRY']['brakesTemperature'][2],
                            "brakesTemperatureRR": self.sanitazed_data[lap][i]['TELEMETRY']['brakesTemperature'][3],
                            
                            # TYRES SURFACE TEMPERATURE
                            "tyresSurfaceTemperatureFL": self.sanitazed_data[lap][i]['TELEMETRY']['tyresSurfaceTemperature'][0],
                            "tyresSurfaceTemperatureFR": self.sanitazed_data[lap][i]['TELEMETRY']['tyresSurfaceTemperature'][1],
                            "tyresSurfaceTemperatureRL": self.sanitazed_data[lap][i]['TELEMETRY']['tyresSurfaceTemperature'][2],
                            "tyresSurfaceTemperatureRR": self.sanitazed_data[lap][i]['TELEMETRY']['tyresSurfaceTemperature'][3],
                            
                            # TYRES INNER TEMPERATURE
                            "tyresInnerTemperatureFL": self.sanitazed_data[lap][i]['TELEMETRY']['tyresInnerTemperature'][0],
                            "tyresInnerTemperatureFR": self.sanitazed_data[lap][i]['TELEMETRY']['tyresInnerTemperature'][1],
                            "tyresInnerTemperatureRL": self.sanitazed_data[lap][i]['TELEMETRY']['tyresInnerTemperature'][2],
                            "tyresInnerTemperatureRR": self.sanitazed_data[lap][i]['TELEMETRY']['tyresInnerTemperature'][3],
                            
                            # TYRES PRESSURE
                            "tyresPressureFL": self.sanitazed_data[lap][i]['TELEMETRY']['tyresPressure'][0],
                            "tyresPressureFR": self.sanitazed_data[lap][i]['TELEMETRY']['tyresPressure'][1],
                            "tyresPressureRL": self.sanitazed_data[lap][i]['TELEMETRY']['tyresPressure'][2],
                            "tyresPressureRR": self.sanitazed_data[lap][i]['TELEMETRY']['tyresPressure'][3],
                            
                            # TYRES WEAR
                            "tyresWearFL": self.sanitazed_data[lap][i]["CAR_DAMAGE"]["tyresWear"][0],
                            "tyresWearFR": self.sanitazed_data[lap][i]["CAR_DAMAGE"]["tyresWear"][1],
                            "tyresWearRL": self.sanitazed_data[lap][i]["CAR_DAMAGE"]["tyresWear"][2],
                            "tyresWearRR": self.sanitazed_data[lap][i]["CAR_DAMAGE"]["tyresWear"][3],                        

                            # MOTION DATA
                            "worldPositionX": self.sanitazed_data[lap][i]['MOTION_DATA']['worldPositionX'],
                            "worldPositionY": self.sanitazed_data[lap][i]['MOTION_DATA']['worldPositionY'],
                            "worldPositionZ": self.sanitazed_data[lap][i]['MOTION_DATA']['worldPositionZ'],
                            "gForceLateral": self.sanitazed_data[lap][i]['MOTION_DATA']['gForceLateral'],
                            "gForceLongitudinal": self.sanitazed_data[lap][i]['MOTION_DATA']['gForceLongitudinal'],
                            "gForceVertical": self.sanitazed_data[lap][i]['MOTION_DATA']['gForceVertical']
                        })                            
                    
            parquet_path = f"analisys/sanitazed_data/{self.track}/{self.session_id}"
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            os.makedirs(parquet_path, exist_ok=True)
            
            
            self.saveParquet(consolidated, f"{parquet_path}/telemetry_{timestamp}.parquet")
            
            out_data = {"parquet": f"telemetry_{timestamp}.parquet", "path": parquet_path}
            if self.is_training:
                self.save_data({"track": self.track, "session": self.session_id, "parquet_path": out_data}, "analisys/sanitazed_data/summary.jsonl")
            
            return out_data
        else:
            return False