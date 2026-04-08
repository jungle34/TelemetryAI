import re

class ArgsHandler:
    def __init__(self, args:list):
        self.args = args
        
        self.debug_mode = False
        self.get_arg_by_type()                
        
    def get_arg_by_type(self):
        for arg in self.args:            
            regex = re.compile(r"(--DEBUG=)(true|false)", flags=re.MULTILINE | re.UNICODE)
            matches = regex.finditer(arg)
            
            for match in matches:
                arg_type = match.groups()[0]
                arg_val = match.groups()[1]
                
                if arg_type == "--DEBUG=":                    
                    self.debug_mode = (arg_val == "true")