# AI-SOC-Analyzer

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Wazuh](https://img.shields.io/badge/Wazuh-4.x-green)](https://wazuh.com/)
[![Security](https://img.shields.io/badge/Security-First-red)](#security-first-design)
[![Lightweight](https://img.shields.io/badge/Dependencies-Minimal-brightgreen)](#design-philosophy)

## Overview

**AI-SOC-Analyzer** is a **privacy-first, fact-verified** security alert analysis system. It automates incident report generation from Wazuh alerts by combining a **local AI model** (Ollama/Gemma 3) with **strict fact verification** to reduce AI hallucinations — a critical requirement in SOC operations.

### Why This Matters

SOC analysts face alert fatigue. Most tools let AI "interpret" alerts freely, risking false positives and invented facts. This project takes a different approach: **verify facts first, then analyze**, and clearly separate the two in the output.

---

## Key Features

| Feature | Why It Matters |
|---------|---------------|
| **Verified Facts Only** | Analysts get only facts extracted directly from Wazuh, clearly separated from AI analysis |
| **Strict Prompt Engineering** | Explicit safety rules instruct the LLM not to invent attacks, compromises, or technical details |
| **Privacy-First** | All processing runs locally (Ollama); zero data sent to cloud APIs or third parties |
| **Minimal Dependencies** | Uses only Python stdlib + local Ollama; reduces supply chain risk and deployment complexity |
| **SOC-Focused Output** | Reports structured for L1 analyst workflow: verified facts → assessment → recommended actions |

---

## Architecture

```
Wazuh Alert (alert.json)
        ↓
   [EXTRACT FACTS ONLY]
        ↓
   Verified Wazuh Data
   • Rule ID, Level, Description
   • Command, PID, Process
   • Denied Operation, Target File
   • Timestamp, Log Source
        ↓
   [STRICT PROMPT RULES]
        ↓
   Ollama + Gemma 3 1B (Local LLM)
        ↓
   Incident Report
   • Alert Summary
   • Verified Evidence
   • Security Assessment
   • Recommended SOC Actions
   • Analyst Conclusion
```

---

## Security-First Design Philosophy

### 1. Fact Verification

```python
# CORRECT: Extract only what's in the alert
verified_facts = {
    "rule_id": alert["rule"]["id"],
    "command": alert["audit"]["command"],
    "denied_operation": parse_audit_log(alert)
}
```

### 2. Strict Prompt Engineering

The LLM receives explicit guardrails (see `analyze_alert.py`, `generate_analysis()` function):

```
STRICT RULES (DO NOT DEVIATE):
- Do not invent facts, IP addresses, or usernames
- Do not say an attack occurred unless explicitly proven
- "denied" means access was BLOCKED, not allowed
- Do not interpret the command "passwd" as proof a password was changed
- Do not invent MITRE ATT&CK techniques
- If uncertain, say: "Not determined from the alert"
```

### 3. Known Limitation — Model Adherence Is Not Guaranteed

Testing showed the local Gemma 3 1B model does **not** always follow the strict rules perfectly. In one test run, the model incorrectly referenced "Kubernetes" (a term not present anywhere in the alert data) and implied a password change had occurred, despite the prompt explicitly prohibiting that interpretation.

This is treated as an important finding, not a hidden flaw: it confirms that **human analyst review of the AI-generated section remains mandatory**, not optional. The verified facts section — not the AI interpretation — remains the authoritative record of the event.

### 4. Analyst-Readable Output

Reports clearly separate:
- **Verified Evidence** (facts only)
- **Security Assessment** (interpretation + uncertainty)
- **Recommended Actions** (concrete next steps)

---

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **SIEM** | Wazuh 4.x | Industry-standard; open-source |
| **Language** | Python 3.8+ | Best for security automation; good stdlib |
| **Local LLM** | Ollama + Gemma 3 1B | Privacy-first; runs offline; minimal resources |
| **Data Format** | JSON | Standard Wazuh alert format |
| **Output** | Plain Text | Human-readable; analyst-friendly |

---

## Prerequisites

- **Wazuh Agent or Manager** (4.x)
- **Ollama** — Download from https://ollama.ai/download
- **Gemma 3 1B Model** — Pulled via `ollama pull gemma3:1b`
- **Python 3.8+**
- **2GB+ RAM** — For running Gemma 3 locally

---

## Quick Start

### Step 1: Install Ollama
```bash
# macOS
brew install ollama

# Linux
curl https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download
```

### Step 2: Pull the Model
```bash
ollama pull gemma3:1b
```

### Step 3: Start Ollama Service
```bash
# In one terminal, keep this running:
ollama serve
```

### Step 4: Run the Analyzer
```bash
# In another terminal:
python analyze_alert.py
```

### Step 5: Review the Report
```bash
cat incident_report.txt
```

---

## Example Workflow

### Input: Wazuh Alert
```json
{
  "rule_id": "80730",
  "level": 3,
  "description": "Auditd: SELinux permission check",
  "command": "passwd",
  "full_log": "avc: denied { write } for pid=17255 path=\"/var/ossec/queue/vd_updater/tmp/contents/file.json\""
}
```

### Output: Incident Report
```
ALERT SUMMARY
An SELinux permission check event was triggered during a system process operation.
The alert indicates that write access was DENIED (blocked).

VERIFIED EVIDENCE
• Rule ID: 80730 (Auditd: SELinux permission check)
• Wazuh Level: 3
• Command: passwd
• Operation: write (DENIED)
• Target: /var/ossec/queue/vd_updater/tmp/contents/file.json

SECURITY ASSESSMENT
This is a routine SELinux enforcement event. The denied write operation
indicates the kernel security module blocked access as designed.

RECOMMENDED SOC ACTIONS
1. Check if this alert is recurring (expected for normal Wazuh operations)
2. Review SELinux policy for the Wazuh user context if frequency increases
3. Cross-reference with Wazuh server logs for context

ANALYST CONCLUSION
No evidence of compromise. This appears to be normal SELinux enforcement.
```

---

## Project Structure

```
ai-soc-analyzer/
├── analyze_alert.py       # Main analyzer with error handling
├── alert.json             # Sample Wazuh alert
├── incident_report.txt    # Generated report (created after first run)
├── requirements.txt       # Setup notes and dependencies
├── README.md              # This file
└── .gitignore
```

---

## Skills Demonstrated

- **SOC Operations** — Alert triage, rule tuning, analyst workflows
- **SIEM Integration** — Parsing Wazuh alerts, extracting actionable data
- **Python Automation** — Lightweight, stdlib-based security scripts
- **AI/LLM Integration** — Prompt engineering, safety constraints, local deployment
- **Security Mindset** — Fact verification, critical evaluation of AI output, audit trail
- **Clean Code** — Docstrings, error handling, modular design

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ConnectionRefusedError` when running script | Run `ollama serve` in another terminal; check it's running on port 11434 |
| `Model not found: gemma3:1b` | Run `ollama pull gemma3:1b` to download the model |
| `FileNotFoundError: alert.json` | Place a Wazuh alert JSON file in the project root (use provided sample) |
| Slow report generation | Gemma 3 on CPU can take 30-60+ seconds. This is normal for local inference. |
| Out of memory | Gemma 3 1B needs ~2GB RAM. Close other applications if needed. |

---

## Future Enhancements

- [ ] Batch processing (multiple alerts per run)
- [ ] SQLite database for alert history & trending
- [ ] REST API for integration with other tools
- [ ] Splunk & ELK SIEM connectors
- [ ] MITRE ATT&CK mapping for rule IDs
- [ ] Real-time Wazuh webhook integration
- [ ] Web dashboard for analyst workflow

---

## License

MIT License — See LICENSE file for details

---

## Author

**Jan Jadoon** | SOC Analyst in Training
GitHub: [jmjadoon](https://github.com/jmjadoon)
BS Computer Science (Gomal University, 2023)
Bano Qabil Cyber Security Fundamentals (Excellence Medal)
The Arzens Offensive Security & VAPT Internship

---

**Last Updated:** August 2026
**Project Status:** Complete (The Arzens Final Internship Project)
