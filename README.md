# AI-SOC-Analyzer

## Overview

AI-SOC-Analyzer is a local AI-assisted Security Operations Center (SOC) alert analysis system.

It takes a Wazuh security alert, extracts verified security facts, sends the alert context to a locally running Gemma 3 model through Ollama, and generates an AI-assisted SOC incident report.

## Architecture

Wazuh Alert
    ↓
alert.json
    ↓
Python Analyzer
    ↓
Ollama / Gemma 3 1B
    ↓
AI SOC Analysis
    ↓
incident_report.txt

## Technologies

- Wazuh
- Python
- Ollama
- Gemma 3 1B
- Windows
- Linux/Wazuh Server
- VS Code

## Current Test Alert

Rule ID: 80730

Rule Description:
Auditd: SELinux permission check.

Wazuh Level:
3

Agent:
wazuh-server

Command:
passwd

Audit Type:
AVC

Operation:
write

Target:
`/var/ossec/queue/vd_updater/tmp/contents/3733504-api_file.json`

Log Source:
`/var/log/audit/audit.log`

## How It Works

1. A Wazuh security alert is stored in `alert.json`.
2. `analyze_alert.py` reads the alert.
3. Verified Wazuh facts are extracted.
4. The alert context is sent to Ollama.
5. Gemma 3 1B generates an AI-assisted security analysis.
6. The result is saved as `incident_report.txt`.

## Running the Analyzer

Start Ollama:

```powershell
ollama serve