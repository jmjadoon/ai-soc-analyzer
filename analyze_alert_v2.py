#!/usr/bin/env python3
"""
AI-SOC-Analyzer: Automated Wazuh Alert Analysis

Reads a Wazuh security alert, extracts verified facts, and generates
an AI-assisted incident report using a local Ollama LLM.

This tool prioritizes fact verification and prevents AI hallucinations
through strict prompt engineering—critical for SOC analysts who need
accuracy over creativity.

Usage:
    python analyze_alert.py

Requirements:
    - Ollama service running locally (ollama serve)
    - Gemma 3 1B model pulled (ollama pull gemma:3b)
    - alert.json in the same directory

Output:
    - incident_report.txt with verified facts and AI analysis
"""

import json
import urllib.request
import urllib.error
import sys
import os
from datetime import datetime


def load_alert(filename: str = "alert.json") -> dict:
    """
    Load and validate Wazuh alert JSON.
    
    Args:
        filename: Path to alert.json file
        
    Returns:
        dict: Parsed alert data
        
    Raises:
        FileNotFoundError: If alert.json doesn't exist
        json.JSONDecodeError: If alert.json is invalid JSON
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Error: {filename} not found. Place a Wazuh alert JSON in this directory.")
    
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Error: {filename} is not valid JSON. {str(e)}", e.doc, e.pos)


def extract_verified_facts(alert: dict) -> dict:
    """
    Extract ONLY verified facts from Wazuh alert.
    
    This function is deliberately conservative—it extracts only facts
    present in the alert JSON, never inferring or inventing details.
    This aligns with SOC best practices: verify before analyze.
    
    Args:
        alert: Parsed Wazuh alert dictionary
        
    Returns:
        dict: Verified facts extracted from alert
    """
    verified_facts = {
        "timestamp": alert.get("timestamp"),
        "agent_name": alert.get("agent", {}).get("name"),
        "agent_id": alert.get("agent", {}).get("id"),
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
    
    # Parse denied operation and target file from audit log
    full_log = alert.get("full_log", "")
    
    denied_operation = "Not determined"
    target_file = "Not determined"
    
    if 'denied { write }' in full_log:
        denied_operation = "write"
    elif 'denied { read }' in full_log:
        denied_operation = "read"
    elif 'denied {' in full_log:
        # Generic denied operation parsing
        denied_operation = full_log.split('denied {')[1].split('}')[0].strip()
    
    if 'path="' in full_log:
        target_file = full_log.split('path="')[1].split('"')[0]
    
    verified_facts["denied_operation"] = denied_operation
    verified_facts["target_file"] = target_file
    
    return verified_facts


def check_ollama_connection(host: str = "127.0.0.1", port: int = 11434, timeout: int = 5) -> bool:
    """
    Check if Ollama service is running and accessible.
    
    Args:
        host: Ollama host (default: localhost)
        port: Ollama port (default: 11434)
        timeout: Connection timeout in seconds
        
    Returns:
        bool: True if Ollama is reachable, False otherwise
    """
    try:
        request = urllib.request.Request(
            f"http://{host}:{port}/api/tags",
            method="GET"
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def generate_analysis(verified_facts: dict, model: str = "gemma:3b") -> str:
    """
    Send verified facts to Ollama LLM and get AI-assisted analysis.
    
    The prompt uses strict safety rules to prevent hallucinations:
    - No invented facts, IP addresses, or usernames
    - No assumptions about successful attacks
    - Clear separation between verified facts and interpretation
    - Explicit denial of false confidence
    
    Args:
        verified_facts: Dictionary of verified alert facts
        model: Ollama model name (default: gemma:3b)
        
    Returns:
        str: AI-generated analysis
        
    Raises:
        urllib.error.URLError: If Ollama connection fails
        json.JSONDecodeError: If response is invalid JSON
    """
    facts_text = json.dumps(verified_facts, indent=2)
    
    # CRITICAL PROMPT: Designed to maximize accuracy and minimize hallucinations
    prompt = f"""You are an L1 SOC Analyst assistant. Analyze ONLY the verified Wazuh alert facts below.

STRICT RULES (DO NOT DEVIATE):

1. Do not invent facts, IP addresses, usernames, permissions, malware, or attack techniques.
2. Do not say an attack or compromise occurred unless the evidence explicitly proves it.
3. Do not interpret the command "passwd" as proof that a password was changed.
4. Do not interpret "write denied" as a successful write—it means access was BLOCKED.
5. Do not change the Wazuh rule level under any circumstances.
6. If something cannot be determined, say: "Not determined from the alert."
7. Clearly separate confirmed facts from possible interpretations.
8. Do not invent MITRE ATT&CK techniques—only reference if alert explicitly mentions them.
9. "denied_operation" means the operation was denied. Never describe it as successful.
10. "command" identifies the recorded command/process. Do not assume what it successfully did.

RETURN EXACTLY THESE SECTIONS:

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

---

VERIFIED WAZUH FACTS (THE ONLY FACTS YOU MAY USE):

{facts_text}
"""
    
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "Error: No response from model")
            
    except urllib.error.URLError as e:
        raise urllib.error.URLError(f"Failed to connect to Ollama at http://127.0.0.1:11434. Is 'ollama serve' running? Error: {str(e)}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON response from Ollama: {str(e)}", e.doc, e.pos)


def format_report(verified_facts: dict, analysis: str) -> str:
    """
    Format the complete incident report combining verified facts and analysis.
    
    Args:
        verified_facts: Dictionary of verified alert facts
        analysis: AI-generated analysis text
        
    Returns:
        str: Formatted incident report
    """
    report = f"""{'='*70}
AI-SOC INCIDENT REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}

VERIFIED WAZUH DATA (FROM ALERT ONLY)
{'-'*70}
Rule ID:          {verified_facts.get('rule_id')}
Wazuh Level:      {verified_facts.get('wazuh_level')}
Description:      {verified_facts.get('rule_description')}
Agent:            {verified_facts.get('agent_name')}
Command:          {verified_facts.get('command')}
Audit Type:       {verified_facts.get('audit_type')}
PID:              {verified_facts.get('audit_pid')}
Operation:        {verified_facts.get('denied_operation')}
Target File:      {verified_facts.get('target_file')}
Log Source:       {verified_facts.get('location')}
Timestamp:        {verified_facts.get('timestamp')}

AI-ASSISTED SOC ANALYSIS
{'-'*70}
{analysis}

{'='*70}
END OF INCIDENT REPORT
{'='*70}
"""
    return report


def main():
    """Main execution flow."""
    print("\n" + "="*70)
    print("AI-SOC-ANALYZER v1.0")
    print("="*70)
    
    try:
        # Step 1: Load alert
        print("\n[1/4] Loading Wazuh alert...", end=" ")
        alert = load_alert()
        print("✓")
        
        # Step 2: Extract verified facts
        print("[2/4] Extracting verified facts...", end=" ")
        verified_facts = extract_verified_facts(alert)
        print("✓")
        
        # Step 3: Check Ollama connection
        print("[3/4] Checking Ollama connection...", end=" ")
        if not check_ollama_connection():
            raise ConnectionError(
                "Ollama service not accessible at http://127.0.0.1:11434\n"
                "Make sure to run: ollama serve (in another terminal)"
            )
        print("✓")
        
        # Step 4: Generate analysis
        print("[4/4] Generating AI analysis (this may take 30-60 seconds)...", end=" ")
        analysis = generate_analysis(verified_facts)
        print("✓")
        
        # Display results
        print("\n" + "="*70)
        print("VERIFIED WAZUH DATA")
        print("="*70)
        print(f"Rule ID: {verified_facts['rule_id']}")
        print(f"Wazuh Level: {verified_facts['wazuh_level']}")
        print(f"Rule: {verified_facts['rule_description']}")
        print(f"Agent: {verified_facts['agent_name']}")
        print(f"Command: {verified_facts['command']}")
        print(f"Operation: {verified_facts['denied_operation']}")
        print(f"Target: {verified_facts['target_file']}")
        
        print("\n" + "="*70)
        print("AI ANALYSIS (First 500 chars)")
        print("="*70)
        print(analysis[:500] + "...\n")
        
        # Save report
        report = format_report(verified_facts, analysis)
        with open("incident_report.txt", "w", encoding="utf-8") as file:
            file.write(report)
        
        print("✓ Full report saved: incident_report.txt")
        print("="*70 + "\n")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
    except ConnectionError as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
