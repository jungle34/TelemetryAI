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