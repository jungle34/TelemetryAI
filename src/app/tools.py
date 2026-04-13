import re

class ArgsHandler:
    def __init__(self, args:list):
        self.args = args
        
        self.debug_mode = False
        self.exit_before = False
                
        self.get_arg_by_type()                
        
    def get_arg_by_type(self):
        for arg in self.args:            
            regex = re.compile(r"--\S+", flags=re.MULTILINE | re.UNICODE)
            matches = regex.finditer(arg)
            
            for match in matches:
                arg_type = match.string.split("=")[0]                
                arg_val = match.string.split("=")[1] == "true" if len(match.string.split("="))>1 else None                
                
                if arg_type == "--DEBUG":                    
                    self.debug_mode = arg_val
                    
                elif arg_type == "--HELP":
                    msg = """TelemetryAI - Execution Help
                    
python main.py {option}

Options:
--DEBUG=true|false - Trigger debug mode state
--HELP             - Open this message, you already did

                    """
                    
                    print(msg)
                    self.exit_before = True
                    
                    
class TrackTranslator:
    def __init__(self):
        self.tracks = {
            0: "Melbourne",
            2: "Shanghai",
            3: "Sakhir (Bahrain)",
            4: "Catalunya",
            5: "Monaco",
            6: "Montreal",
            7: "Silverstone",
            9: "Hungaroring",
            10: "Spa",
            11: "Monza",
            12: "Singapore",
            13: "Suzuka",
            14: "Abu Dhabi",
            15: "Texas",
            16: "Brazil",
            17: "Austria",
            19: "Mexico",
            20: "Baku (Azerbaijan)",
            26: "Zandvoort",
            27: "Imola",
            29: "Jeddah",
            30: "Miami",
            31: "Las Vegas",
            32: "Losail",
            39: "Silverstone (Reverse)",
            40: "Austria (Reverse)",
            41: "Zandvoort (Reverse)"
        }    
    
    def translate(self, track_id:int)->str:
        return self.tracks[track_id]
    
class SessionTypeTranslator:
    def __init__(self):
        self.session_types = {
            0: "Unknown",
            1: "Practice 1",
            2: "Practice 2",
            3: "Practice 3",
            4: "Short Practice",
            5: "Qualifying 1",
            6: "Qualifying 2",
            7: "Qualifying 3",
            8: "Short Qualifying",
            9: "One-Shot Qualifying",
            10: "Sprint Shootout 1",
            11: "Sprint Shootout 2",
            12: "Sprint Shootout 3",
            13: "Short Sprint Shootout",
            14: "One-Shot Sprint Shootout",
            15: "Race",
            16: "Race 2",
            17: "Race 3",
            18: "Time Trial"
        }
        
    def translate(self, session_type_id:int)->str:
        return self.session_types[session_type_id]
    
class WeatherTranslator:
    def __init__(self):
        self.weather_conditions = {
            0: "Céu limpo",
            1: "Poucas nuvens",
            2: "Encoberto",
            3: "Chuva leve",
            4: "Chuva forte",
            5: "Tempestade"
        }
    
    def translate(self, weather_id:int)->str:
        return self.weather_conditions[weather_id]