# Mastermind Bug Bounty

Four-phase autonomous bug bounty orchestration.

Mastermind is not a traditional scanner. It is a workflow system for AI agents: Python performs deterministic collection and verifier support, while the AI owns interpretation, prioritization, attack reasoning, and autonomous direction changes.

## Pipeline

```text
Phase 0 | Asset Recon
  ↓
Phase 1 | Attack Surface Analysis
  ↓
Phase 2 | Autonomous Attack
  ↓
Phase 3 | Report Generation
```

## Phase 0 | Asset Recon

The AI receives one goal:

> Map every externally exposed asset for this target.

It receives a capability list, not a fixed order:

- DNS resolution
- Subdomain enumeration
- JS download
- sourcemap download
- source leak search
- Swagger/OpenAPI exposure probing
- common path dictionary probing

Python handles deterministic execution:

- Batch download JS and sourcemaps
- Extract API endpoints, methods, parameters, auth hints, and login routes from JS
- Probe Swagger/OpenAPI exposure
- Run common path dictionaries
- Produce structured outputs such as `_endpoint_params.json`

The AI then interprets the output. For example, if Actuator and Druid are both exposed, the AI should infer a Spring Boot exposure cluster without waiting for a hard-coded rule.

## Phase 1 | Attack Surface Analysis

No active testing happens here.

The AI ranks attack surfaces and explains:

- priority
- reasoning
- likely vulnerability direction
- planned test approach
- possible attack-chain connections
- credential needs, including login URL when credentials are requested

## Phase 2 | Autonomous Attack

Core rule:

> Test attack surfaces by priority. After each test, decide independently whether to continue, change direction, or stop. Do not ask the user whether to continue. Stop only after all surfaces are tested, a confirmed high-risk issue is found, or five consecutive attempts make no progress.

Loop:

1. Pick an attack surface
2. Form a vulnerability hypothesis
3. Design and run a test
4. Interpret the result
5. If uncertain, try a different angle
6. If disproven, log the negative result and move on
7. If a new surface appears, append it to the queue
8. Stop only when a stop condition is met

Python support in this phase:

- blind probing
- response mining
- `_endpoint_params.json × _leaked_values.json` value-pool linkage
- HTTP method and Content-Type fallback
- Pair Completeness Gate

## Phase 3 | Report Generation

This phase is intentionally rigid. Only verifier-confirmed findings are reported.

Required fields:

- title
- vulnerability type
- severity
- URL
- reproduction steps
- evidence
- remediation

Rules:

- evidence must be verifiable
- no speculation
- no exaggerated impact
- PENDING/INFO items stay out of the main report

## Usage

```bash
python cli.py phases
python cli.py run --target https://example.com --hunt-dir ./hunt-data
python cli.py status --hunt-dir ./hunt-data
python cli.py resume --hunt-dir ./hunt-data
```

## Project Map

```text
SKILL.md                 Main four-phase skill
workflow/pipeline.py     Pipeline definition
workflow/tasks.py        Deterministic task library
shared/linkage.py        Value-pool linkage engine
agents/                  Agent role instructions
skills/                  Domain-specific testing skills
references/              Knowledge base and report/compliance references
scripts/                 Standalone hook scripts
tests/                   Core logic tests
```

## Verify

```bash
python tests/test_linkage.py
```
