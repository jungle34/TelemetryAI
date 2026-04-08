import threading
from src.udp.telemetry_UDP import F1TelemetryServer

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
            
    def getLaps(self):
        return "Olá"
    
    def getModule(self, module:str):
        with open(f"views/modules/{module}/index.html", "r", encoding="utf-8") as file:
            return file.read()            
        
    def getLapHistory(self):
        return "Olá"