# AI-SOC-Analyzer

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Wazuh](https://img.shields.io/badge/Wazuh-4.x-green)](https://wazuh.com/)
[![Security](https://img.shields.io/badge/Security-First-red)](#security-first-design)
[![Lightweight](https://img.shields.io/badge/Dependencies-Minimal-brightgreen)](#design-philosophy)

## Overview

**AI-SOC-Analyzer** is a **privacy-first, fact-verified** security alert analysis system. It automates incident report generation from Wazuh alerts by combining **local AI models** (Ollama/Gemma 3) with **strict fact verification** to eliminate AI hallucinations—a critical requirement in SOC operations.

### Why This Matters

SOC analysts face alert fatigue. Most tools let AI "interpret" alerts freely, risking false positives and invented facts. This project takes a different approach: **verify facts first, then analyze**. It's production-grade thinking for a real problem.

---

## 🎯 Key Features

| Feature | Why It Matters |
|---------|---------------|
| **Verified Facts Only** | Prevents AI hallucinations; analysts get only facts from Wazuh, clearly separated from analysis |
| **Strict Prompt Engineering** | 10 explicit safety rules prevent the LLM from inventing attacks, compromises, or technical details |
| **Privacy-First** | All processing runs locally (Ollama); zero data sent to cloud APIs or third parties |
| **Minimal Dependencies** | Uses only Python stdlib + local Ollama; reduces supply chain risk and deployment complexity |
| **SOC-Focused Output** | Reports structured for L1 analyst workflow: verified facts → assessment → recommended actions |
| **Extensible** | Easy to integrate with Splunk, ELK, or other SIEMs via webhook adapters |

---

## 🏗️ Architecture

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
   ├─ Cannot invent facts
   ├─ Cannot assume successful attacks
   ├─ Cannot interpret "denied" as "allowed"
   └─ Must cite verified facts only
        ↓
   Incident Report
   • Alert Summary
   • Verified Evidence
   • Security Assessment
   • Recommended SOC Actions
   • Analyst Conclusion
```

---

## 🔒 Security-First Design Philosophy

This project embodies **SOC best practices**:

### 1. **Fact Verification**
```python
# ✓ CORRECT: Extract only what's in the alert
verified_facts = {
    "rule_id": alert["rule"]["id"],
    "command": alert["audit"]["command"],
    "denied_operation": parse_audit_log(alert)
}

# ✗ WRONG: Invent or assume details
"username": "admin",  # NOT in alert
"attack_type": "privilege escalation",  # NOT verified
"severity": "critical"  # Wazuh already said level 3
```

### 2. **Strict Prompt Engineering**
The LLM receives **explicit guardrails** (see `analyze_alert.py` lines 110-135):

```
STRICT RULES (DO NOT DEVIATE):
1. Do not invent facts, IP addresses, or usernames
2. Do not say an attack occurred unless explicitly proven
3. "denied" means access was BLOCKED, not allowed
4. Do not invent MITRE ATT&CK techniques
5. If uncertain, say: "Not determined from the alert"
```

This prevents common AI failures:
- ❌ "Password change succeeded" (actually denied)
- ❌ "Privilege escalation attempt" (no evidence)
- ❌ "Likely malware" (not in alert)

### 3. **Analyst-Readable Output**
Reports clearly separate:
- **Verified Evidence** (facts only)
- **Security Assessment** (interpretation + uncertainty)
- **Recommended Actions** (concrete next steps)

---

## 🛠️ Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **SIEM** | Wazuh 4.x | Industry-standard; open-source |
| **Language** | Python 3.8+ | Best for security automation; good stdlib |
| **Local LLM** | Ollama + Gemma 3 1B | Privacy-first; runs offline; minimal resources |
| **Data Format** | JSON | Standard Wazuh alert format |
| **Output** | Plain Text | Human-readable; analyst-friendly; no bloat |

---

## 📋 Prerequisites

✅ **Wazuh Agent or Manager** (4.x)  
✅ **Ollama** — Download from https://ollama.ai/download  
✅ **Gemma 3 1B Model** — Pulled via `ollama pull gemma:3b`  
✅ **Python 3.8+** — Most systems include this  
✅ **2GB+ RAM** — For running Gemma 3 locally  

---

## 🚀 Quick Start

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
ollama pull gemma:3b
```
(First run downloads ~2GB; subsequent runs are instant)

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

## 📊 Example Workflow

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
The Wazuh level (3) reflects low severity.

RECOMMENDED SOC ACTIONS
1. Check if this alert is recurring (expected for normal Wazuh operations)
2. Review SELinux policy for the Wazuh user context if frequency increases
3. Cross-reference with Wazuh server logs for context

ANALYST CONCLUSION
No evidence of compromise. This appears to be normal SELinux enforcement.
```

---

## 📁 Project Structure

```
ai-soc-analyzer/
├── analyze_alert.py          # Main analyzer (improved v2 with error handling)
├── alert.json                # Sample Wazuh alert
├── alert_backup.json         # Real-world example alert
├── incident_report.txt       # Generated report (created after first run)
├── requirements.txt          # Dependencies (minimal)
├── README.md                 # This file
└── .gitignore
```

---

## 🔧 How It Works (Technical Deep Dive)

### 1. Alert Ingestion
```python
# Load Wazuh alert JSON
alert = json.load("alert.json")
```

### 2. Fact Extraction (Conservative)
```python
# Extract ONLY verified data—never invent
verified_facts = {
    "rule_id": alert["rule"]["id"],           # Verified
    "command": alert["audit"]["command"],     # Verified
    "denied_operation": parse_audit_log(),    # Parsed from log
    # NOT included: "username", "attack_type", etc. (not in alert)
}
```

### 3. Strict Prompt Construction
```python
# Send verified facts + safety rules to LLM
prompt = f"""
STRICT RULES (DO NOT DEVIATE):
- Do not invent facts
- "denied" means access was BLOCKED
- Do not assume successful attacks
[...10 more rules...]

VERIFIED FACTS (the only source of truth):
{verified_facts}
"""
```

### 4. LLM Analysis (Local)
```python
# Call local Ollama (no internet required)
response = ollama.generate(
    model="gemma:3b",
    prompt=prompt
)
```

### 5. Report Generation
```python
# Combine verified facts + AI analysis into structured report
report = format_report(verified_facts, analysis)
```

---

## 📊 Skills Demonstrated

This project showcases:

- **SOC Operations** — Alert triage, rule tuning, analyst workflows
- **SIEM Integration** — Parsing Wazuh alerts, extracting actionable data
- **Python Automation** — Lightweight, stdlib-based security scripts
- **AI/LLM Integration** — Prompt engineering, safety constraints, local deployment
- **Security Mindset** — Fact verification, preventing hallucinations, audit trail
- **Clean Code** — Docstrings, error handling, modular design

---

## ⚙️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `ConnectionRefusedError` when running script | Run `ollama serve` in another terminal; check it's running on port 11434 |
| `Model not found: gemma:3b` | Run `ollama pull gemma:3b` to download the model (~2GB) |
| `FileNotFoundError: alert.json` | Place a Wazuh alert JSON file in the project root (use provided sample) |
| `ModuleNotFoundError` | You shouldn't see this—the project uses only stdlib. Python 3.8+ should work. |
| Slow report generation | Gemma 3 on CPU takes 30-60 seconds. This is normal for local inference. |
| Out of memory | Gemma 3 1B needs ~2GB RAM. Close other applications or use a smaller model (`ollama pull tinyllama`) |

---

## 🚀 Future Enhancements

- [ ] Batch processing (multiple alerts per run)
- [ ] SQLite database for alert history & trending
- [ ] REST API for integration with other tools
- [ ] Splunk & ELK SIEM connectors
- [ ] MITRE ATT&CK mapping for rule IDs
- [ ] Machine learning-based alert severity re-scoring
- [ ] Real-time Wazuh webhook integration
- [ ] Dashboard for analyst workflow

---

## 📚 Learning Resources

- **Wazuh Docs** — https://documentation.wazuh.com/
- **SOC Best Practices** — https://owasp.org/www-project-soc-project/
- **Ollama Models** — https://ollama.ai/library
- **Prompt Engineering for Security** — OpenAI/Anthropic guidelines
- **MITRE ATT&CK** — https://attack.mitre.org/

---

## 📄 License

MIT License — See LICENSE file for details

---

## 👤 Author

**Jan Jadoon** | SOC Analyst in Training  
📧 [jmjadoon1 on Fiverr](https://fiverr.com/jmjadoon1) (5.0 ⭐)  
💻 [GitHub: jmjadoon](https://github.com/jmjadoon)  
🎓 BS Computer Science (Gomal University, 2023)  
🏆 Bano Qabil Cyber Security Fundamentals (Excellence Medal)  
🛡️ The Arzens Offensive Security & VAPT Internship  

---

## 🎯 For Recruiters & Interviewers

**What This Project Shows:**

1. **Security Maturity** — You understand that AI + security requires guardrails, not freedom
2. **SOC Thinking** — Alert triage, fact verification, and analyst workflows
3. **Clean Code** — Docstrings, error handling, modular design
4. **Privacy-First Architecture** — Local processing, zero cloud dependency
5. **Production Readiness** — Error handling, logging, extensibility

**Interview Talking Points:**

- "I built an AI-SOC analyzer that prevents the LLM from hallucinating. This is critical in security—analysts need accuracy over creativity."
- "All processing runs locally using Ollama. No data leaves the organization."
- "The prompt has 10 explicit safety rules. This is how you do responsible AI in security ops."
- "It's designed to work with Wazuh, which I know many SOCs use in production."

---

**Last Updated:** August 2026  
**Project Status:** Complete (The Arzens Week 4 Final Project)
