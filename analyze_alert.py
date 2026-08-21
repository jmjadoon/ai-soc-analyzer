import json
import urllib.request
# Load Wazuh alert
with open("alert.json", "r", encoding="utf-8") as file:
    alert = json.load(file)

# Extract VERIFIED information from the Wazuh alert
verified_facts = {
    "timestamp": alert.get("timestamp"),
    "agent_name": alert.get("agent", {}).get("name"),
    "rule_id": alert.get("rule", {}).get("id"),
    "wazuh_level": alert.get("rule", {}).get("level"),
    "rule_description": alert.get("rule", {}).get("description"),
    "rule_groups": alert.get("rule", {}).get("groups"),
    "audit_pid": alert.get("audit", {}).get("pid"),
    "audit_id": alert.get("audit", {}).get("id"),
    "audit_type": alert.get("audit", {}).get("type"),
    "command": alert.get("audit", {}).get("command"),
    "location": alert.get("location"),
    "decoder": alert.get("decoder"),
    "full_log": alert.get("full_log")
}


# Extract the denied operation and target file from the audit log
full_log = alert.get("full_log", "")

denied_operation = "Not determined"
target_file = "Not determined"

if 'denied { write }' in full_log:
    denied_operation = "write"

if 'path="' in full_log:
    target_file = full_log.split('path="')[1].split('"')[0]

verified_facts["denied_operation"] = denied_operation
verified_facts["target_file"] = target_file

facts_text = json.dumps(verified_facts, indent=2)

# AI prompt
prompt = f"""
You are an L1 SOC Analyst assistant.

Analyze ONLY the verified Wazuh alert facts below.

STRICT RULES:

1. Do not invent facts.
2. Do not invent IP addresses, usernames, permissions, malware,
   attack techniques, or successful actions.
3. Do not say that an attack or compromise occurred unless the
   evidence explicitly proves it.
4. Do not interpret the command "passwd" as proof that a password
   was changed.
5. Do not interpret "write denied" as a successful write.
6. Do not change the Wazuh rule level.
7. If something cannot be determined, say:
   "Not determined from the alert."
8. Clearly separate confirmed facts from possible interpretations.
9. Do not invent a MITRE ATT&CK technique.
10. "denied_operation" means the operation was denied. Never describe it as successful.
11. "command" identifies the recorded command/process associated with the event. Do not assume what the command successfully did.

Return exactly these sections:

ALERT SUMMARY
Explain what the alert records.

VERIFIED EVIDENCE
List only facts directly present in the supplied data.

WAZUH SEVERITY
State the exact Wazuh rule level.

SECURITY ASSESSMENT
Explain what the event may mean, but clearly identify uncertainty.

RECOMMENDED SOC ACTIONS
Give practical investigation steps.

ANALYST CONCLUSION
State what is known and what cannot be determined.

VERIFIED WAZUH FACTS:

{facts_text}
"""

# Send request to local Ollama
data = {
    "model": "gemma3:1b",
    "prompt": prompt,
    "stream": False
}

request = urllib.request.Request(
    "http://127.0.0.1:11434/api/generate",
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(request) as response:
    result = json.loads(response.read().decode("utf-8"))

# Display verified Wazuh information
print("\n" + "=" * 60)
print("AI SOC INCIDENT ANALYSIS")
print("=" * 60)

print("\nVERIFIED WAZUH DATA")
print("-" * 60)
print(f"Rule ID: {verified_facts['rule_id']}")
print(f"Wazuh Level: {verified_facts['wazuh_level']}")
print(f"Rule Description: {verified_facts['rule_description']}")
print(f"Agent: {verified_facts['agent_name']}")
print(f"Command: {verified_facts['command']}")
print(f"Audit Type: {verified_facts['audit_type']}")
print(f"PID: {verified_facts['audit_pid']}")
print(f"Operation: {verified_facts['denied_operation']}")
print(f"Target File: {verified_facts['target_file']}")
print(f"Log Source: {verified_facts['location']}")

print("\nAI ANALYSIS")
print("-" * 60)
print(result["response"])

print("\n" + "=" * 60)
# Save the complete analysis as an incident report
report = f"""
============================================================
AI SOC INCIDENT REPORT
============================================================

VERIFIED WAZUH DATA
------------------------------------------------------------
Rule ID: {verified_facts['rule_id']}
Wazuh Level: {verified_facts['wazuh_level']}
Rule Description: {verified_facts['rule_description']}
Agent: {verified_facts['agent_name']}
Command: {verified_facts['command']}
Audit Type: {verified_facts['audit_type']}
PID: {verified_facts['audit_pid']}
Operation: {verified_facts['denied_operation']}
Target File: {verified_facts['target_file']}
Log Source: {verified_facts['location']}
Timestamp: {verified_facts['timestamp']}

AI SOC ANALYSIS
------------------------------------------------------------
{result["response"]}

============================================================
END OF INCIDENT REPORT
============================================================
"""

with open("incident_report.txt", "w", encoding="utf-8") as file:
    file.write(report)

print("\nIncident report saved successfully:")
print("incident_report.txt")