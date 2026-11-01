netauto-lab
A hands-on network automation portfolio: Ansible, Terraform, Python, RESTCONF/YANG, CI/CD, streaming telemetry, Cisco NSO and AI-assisted operations, built and tested against simulated Cisco devices in Cisco Modeling Labs (CML) and Cisco DevNet sandboxes.

The goal of this repo is to show how I approach network automation in practice: declarative configuration, repeatable pipelines, validation before and after every change, and safe handling of credentials.

A secondary objective is preparation for the Cisco CCNP Automation (AUTOCOR 350-901) exam. The labs are mapped to the exam blueprint, but they are written as working automation, not exam notes.

Lab use only. Everything here runs against CML nodes and DevNet sandboxes. No production configurations, hostnames, addresses or credentials are included.
What this repo demonstrates
Area
What I built
Tools
Ansible
Idempotent playbooks for VLANs, OSPF and ACLs on IOS/IOS-XE and NX-OS; dynamic inventory driven by a source-of-truth file; secrets kept in ansible-vault
Ansible Core, cisco.ios, cisco.nxos
Terraform
Infrastructure-as-code for Cisco ACI (tenant, VRF, bridge domain) against the reservable DevNet APIC sandbox; plan/apply/targeted destroy workflow
Terraform, ciscodevnet/aci provider
Python
Multi-device config push with threading and error handling; paginated REST client with token reuse and exponential backoff; syslog and webhook receivers; Vault-backed credentials and input validation
Python, Netmiko, requests, uv, hvac
Model-driven APIs
RESTCONF requests built from YANG models, JSON and YAML payload construction and validation
YANG Suite, Bruno, cURL
CI/CD
Four-stage GitLab pipeline: build/lint, pre-validation, deploy, post-validation with before/after diff
GitLab CE, Docker, pyATS, CML API
Validation
Before/after state capture and diffing that fails the pipeline on unexpected changes
pyATS
Telemetry
Model-driven telemetry into a Telegraf, InfluxDB and Grafana stack
Docker Compose, gNMI/NETCONF dial-out
Cisco NSO
Add, change and delete device config via NSO CLI and RESTCONF, with dry-run, drift detection and rollback
Cisco NSO, netsim
AI in automation
MCP server exposing read-only and write-gated network tools, plus a conversational agent with allow-lists, human confirmation and audit logging
Python, FastMCP

Highlights
Python
Scripts for pushing and verifying device configuration at scale. Features include YAML-driven input, parallel execution with ThreadPoolExecutor, per-device pass/fail reporting, graceful handling of unreachable devices and authentication failures, and a REST client that handles pagination, bearer tokens and HTTP 429 backoff. Projects are managed with uv and locked with uv.lock.
Ansible
Playbooks for Layer 2 and Layer 3 configuration (VLANs, OSPF, ACLs) that are safe to re-run. Inventory can be generated from a source-of-truth file, so a role or site change in the data propagates without editing playbooks. NX-OS coverage compares cisco.nxos modules against the IOS equivalents.
Terraform
ACI objects defined as code and managed through the plan, apply and destroy cycle. The focus is predicting and reviewing changes (terraform plan diffs), safe partial teardown with -target, and keeping state and credentials out of version control.
Repository layout
netauto-lab/

├── ansible/        # Playbooks, inventories, roles, dynamic inventory

├── terraform/      # ACI tenant, VRF and bridge domain

├── python/         # Netmiko, REST client, syslog/webhook, Vault, pyATS helpers

├── restconf-yang/  # RESTCONF payloads (JSON/YAML) and YANG notes

├── cicd/           # GitLab CI pipelines, CML topology YAML

├── docker/         # Telegraf / InfluxDB / Grafana compose stacks

├── pyats/          # Testbeds and change-validation jobs

├── ai-mcp/         # FastMCP server and conversational agent

├── nso/            # Cisco NSO quick-start: CLI and RESTCONF add/change/delete

├── k8s/            # Dockerfile, CronJob and Secret manifests

└── README.md

Each folder has its own README with prerequisites, run steps and expected output.
Lab environment
Cisco Modeling Labs (IOSv, IOSvL2, Catalyst 8000V, NX-OS 9000v)
Ubuntu 24.04 automation workstation
Cisco DevNet reservable APIC sandbox (ACI/Terraform)
Docker, GitLab CE, HashiCorp Vault (dev mode), Cisco NSO with netsim devices
Security practices
No credentials, tokens or private keys are committed. Secrets are supplied through environment variables, ansible-vault or HashiCorp Vault.
.gitignore excludes state files, key material and generated run-time directories.
Automation that changes devices uses dry-run or diff first, and AI-driven tools require explicit confirmation for any write action.
CCNP AUTOCOR (350-901) mapping
The labs are mapped to the exam blueprint domains: Network Automation, Infrastructure as Code, Operations, and AI in Automation. Lab names reference their blueprint objective (for example, "Lab 1.2, Objective 1.2"), so each lab can be traced back to the exam topic it covers.
About
Dave Murphy, Network Automation Engineer. LinkedIn: 
License
MIT. See LICENSE.
