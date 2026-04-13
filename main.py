# LOCAL IMPORTS INTO src/
import src.app.events as events
from src.app.api import Api
from src.app.tools import ArgsHandler

# LIBS
import sys
import webview

args = ArgsHandler(sys.argv)

if args.exit_before:    
    exit()    

api = Api()
window = webview.create_window(
    "TelemetryAI",
    "views/index.html",
    js_api=api    
)

window.events.closed += events.on_closed

webview.start(debug=args.debug_mode)