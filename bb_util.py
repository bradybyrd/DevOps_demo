#  BB lib - Python Helper
import datetime
import json
import os
import sys
import subprocess
import base64

class Util:
    def __init__(self, secrets = []):
        self.secrets = secrets
        self.somthin = "more"
        self.cypher = "kKsjtn60239gjm4ifdjglkw3958671kmdlJJ$$e3"

    def init_log():
        self.logit("#------------- New Run ---------------#")

    def add_secret(self, item):
        self.secrets.append(str(item))

    def logit(self, message, log_type = "INFO", display_only = True):
        cur_date = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        stamp = f"{cur_date}|{log_type}> "
        for line in message.splitlines():
            if log_type == "SECRET":
                cleaned = self.sanitize(line)
            else:
                cleaned = line
            print(f"{stamp}{cleaned}")

    def message_box(self, msg, mtype = "sep"):
        tot = 100
        start = ""
        res = ""
        msg = msg[0:84] if len(msg) > 85 else msg
        ilen = tot - len(msg)
        if (mtype == "sep"):
            start = f'#{"-" * int(ilen/2)} {msg}'
            res = f'{start}{"-" * (tot - len(start) + 1)}#'
        else:
            res = f'#{"-" * tot}#\n'
            start = f'#{" " * int(ilen/2)} {msg} '
            res += f'{start}{" " * (tot - len(start) + 1)}#\n'
            res += f'#{"-" * tot}#\n'

        self.logit(self.sanitize(res))
        return res

    def sanitize(self, txt):
        cleaned = str(txt).strip()
        for item in self.secrets:
            cleaned = cleaned.replace(item, "*******")
        return cleaned

    def run_shell(self, cmd = ["ls", "-l"], details = {}):
        quiet = "quiet" in details
        if not quiet:
            self.logit(f'Running: {" ".join(cmd)}')
        if "dir" in details:
            rawresult = subprocess.run(cmd, capture_output=True, cwd=details["dir"])
        else:
            rawresult = subprocess.run(cmd, capture_output=True)
        if not quiet:
            self.logit("The exit code was: %d" % rawresult.returncode)
        if not quiet:
            self.logit("#--------------- STDOUT ---------------#")
        stdout = rawresult.stdout.decode('ascii')
        stderr = ""
        if not quiet:
            self.logit(stdout)
        if rawresult.stderr:
            if not quiet:
                self.logit("#--------------- STDERR ---------------#")
            stderr = rawresult.stderr.decode('ascii')
            if not quiet:
                self.logit(stderr)    
        return {"cmd" : cmd, "stdout" : stdout, "stderr" : stderr, "returncode" : rawresult.returncode}

    def separator(self, ilength = 102):
        dashy = "-" * (ilength - 2)
        self.logit(f'#{dashy}#')

    def print_timer(self, starttime):
        elapsed = datetime.datetime.now() - starttime
        self.logit(f'Elapsed time: {str(elapsed)}')

    def process_args(self, arglist):
        args = {}
        for arg in arglist:
            pair = arg.split("=")
            if len(pair) > 1:
                args[pair[0].strip()] = "=".join(pair[1:]).strip()
            else:
                args[arg] = ""
        return args
    
    def read_file(self,filepath):
        result = ""
        with open(filepaath, "r") as fil:
            result = fil.read()
        return result
    
    def read_json(self, json_file, is_path = True):
        result = {}
        if is_path:
            with open(json_file) as jsonfile:
                result = json.load(jsonfile)
        else:
            result = json.loads(json_file)
        return result
    
    def save_json(self, json_file, data, is_path = True):
        if is_path:
            with open(json_file, 'w+') as outfile:
                outfile.write(json.dumps(data, indent=2, sort_keys=False, default=str))
        else:
            result =json.dump(data, outfile)

    def desecret(self,txt):
        #message_bytes = txt.replace(self.cypher,"")[::-1].encode('ascii')
        message_bytes = txt.encode('utf-8')
        bytesdecode = base64.b64decode(message_bytes)
        message = bytesdecode.decode('utf-8')
        #print(message)
        #return(message.replace(f'{self.cypher}xx',''))
        return(message)

    def secret(self,txt):
        #message_bytes = f'{self.cypher}xx{txt}'.encode('ascii')
        message_bytes = txt.encode('utf-8')
        base64_bytes = base64.b64encode(message_bytes)
        message = base64_bytes.decode('utf-8')
        #return(f'{message[::-1]}{self.cypher}')
        return(message)
