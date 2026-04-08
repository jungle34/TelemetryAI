# LOCAL IMPORTS INTO src/
import src.events as events
from src.api import Api
from src.tools import ArgsHandler

# LIBS
import sys
import webview

args = ArgsHandler(sys.argv)

api = Api()
window = webview.create_window(
    "Session Manager",
    "views/index.html",
    js_api=api    
)

window.events.closed += events.on_closed

webview.start(debug=args.debug_mode)