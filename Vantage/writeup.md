Sherlock Forensic Writeup: Vantage
--------------------------------------

1. Investigation Overview
Provide a brief summary of the incident. Note that the investigation focused on analyzing network traffic logs and web server activities to determine the source of unauthorized access and potential data exfiltration.

2. Methodology
List the tools used for the investigation, such as:
- Wireshark: For analyzing .pcap files (e.g., controller.2025-07-01.pcap and web-server.2025-07-01.pcap).
- Timeline analysis: For correlating HTTP requests with system logs.

3. Key Investigation Findings
- Reconnaissance: Detail the discovery of subdomain fuzzing and identify the tool used (e.g., ffuf)[cite: 1].
- Access Analysis: Summarize the analysis of POST requests to login endpoints to identify the volume of failed brute-force attempts[cite: 1].
- Exfiltration/Interaction: Document the interactions with OpenStack services or any sensitive data that was accessed or downloaded[cite: 1].

4. Conclusion
Summarize the attacker's trajectory, starting from initial reconnaissance through to the final unauthorized activity identified in the logs[cite: 1].
