### Windows Fundamentals: Lab Summary & Results

---

#### I. Security & Permissions Configuration
Q: Which tab is used to configure NTFS permissions for a file or folder?
A: The Security tab.

Q: By default, which group is often present in the Access Control List (ACL) of new share permissions?
A: The Everyone group.

---

#### II. Identity & Access Management
Q: What is the SID for the user account "Jim"?
A: S-1-5-21-2614195641-1726409526-3792725429-1006

Q: What is the SID for the security group "HR"?
A: S-1-5-21-2614195641-1726409526-3792725429-1007

---

#### III. System Services
Q: What is the official service name for the Windows Update component?
A: wuauserv

---

#### IV. Administrative Notes
- Elevation Requirement: All user and group management tasks require an elevated PowerShell session (Run as Administrator).
- Verification: Use Get-LocalUser and Get-LocalGroup to confirm creation.
