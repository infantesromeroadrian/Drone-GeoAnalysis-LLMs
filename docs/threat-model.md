# Threat model

Scope: the mission-planning and execution path of this prototype (LLM planner, validator, approval, executor, controllers) in simulation. Video analysis (YOLO) is considered only where its output could reach the planner.

Framework versions checked against their primary sources on 2026-11-07: OWASP Top 10 for LLM Applications **2025** (genai.owasp.org) and MITRE ATLAS **v5.6.0** (`dist/ATLAS.yaml`, mitre-atlas/atlas-data).

## Assets

| Asset | Why it matters |
|---|---|
| Commands that reach a controller (`move_to`, `take_off`, mission execution) | Physical consequences (collision, loss of the aircraft, airspace violation) |
| The approval decision | The only point where a human takes responsibility for a flight |
| Envelope configuration | Defines what "safe" means |
| Stored mission files (`missions/`) | Plans persist on disk between validation and execution |

## Actors and trust boundaries

| Actor / input | Trust |
|---|---|
| Operator (authenticated by `OPERATOR_API_KEY` for approvals) | Trusted to approve, not trusted to be correct: a malicious or careless operator can ask for anything |
| Free-text order from an operator or API client | Untrusted data |
| `situation_report` text during flight | Untrusted data (latent channel: no LLM consumes it today) |
| Text recognised in video (signs, overlays) | Untrusted data (latent: no path to the planner today) |
| LLM output (plans, tool calls, amendments) | Untrusted: treated as if attacker-controlled |
| Server process, envelope, gate | Trusted computing base |

The design assumes the LLM is compromised. Prompt hardening is kept as defence in depth, not as a control.

## Threats, controls and residual risk

| # | Threat | Control | Residual risk |
|---|---|---|---|
| T1 | **Malicious or careless operator** asks in plain words for an unsafe flight (300 m, a restricted zone, 3 km away, a forbidden action, 40 min on a 20 min battery) | Envelope rejects the resulting plan whatever the model produced; measured on a real LLM | An operator can still approve a harmful plan that is inside the envelope. The envelope bounds geometry, time and actions, not intent |
| T2 | **Prompt injection through the order** (LLM01, ATLAS AML.T0051.000) | Delimited untrusted input and strict output schema (mitigation); envelope (guarantee) | Injection may still change what the model proposes, within the envelope. Not measured with injection corpora: only plain orders were measured |
| T3 | **Indirect injection through `situation_report`** (LLM01, AML.T0051.001) | `adaptive_control` is a keyword stub today, so no LLM reads the report. Any amendment is parsed with `MissionAmendment` (strict schema); new coordinates need a new envelope check and a new approval | **Not measured** (no consumer). If an LLM is attached later, the amendment path is already gated |
| T4 | **Indirect injection through text in video** (AML.T0051.001) | No path from YOLO/vision output to the mission planner in this code base; same gate if one is added | Not measured; relies on the absence of a path, which must be re-checked when features change (the route-inventory test fails on new motion call sites) |
| T5 | **Compromised LLM** emits a violating plan, tool call or amendment (LLM06 Excessive Agency, AML.T0053) | Single control point; agent tools have no access to drones or the gate; `ApprovedMission` capability; controller guard; tests "compromised LLM" and "no alternative route" | In-process arbitrary code execution is out of scope |
| T6 | **Time-of-check/time-of-use**: stored mission file changed after validation or approval | Hash binding; the gate reloads and re-hashes at execution; token burned on mismatch | An attacker who can also obtain a valid token for the *new* content already passed the envelope and the operator |
| T7 | **Token theft, replay, premature use** | 256-bit random token, single use, 300 s TTL, bound to mission id and hash; only its SHA-256 is stored; audit stores short hashes | Theft of a live token within its TTL by someone who can also call the execute endpoint |
| T8 | **Approval by the LLM or its tools** | Approval needs `X-Operator-Key`; the key is not available to the planner or tools; approvals disabled when unset | A deployment that exposes the key to the model is out of model |
| T9 | **Execution somewhere else than approved** | Home recorded at approval; drone must be within 10 m at start; geofence anchored to home | GNSS spoofing is out of scope |
| T10 | **Direct manual motion commands** | `move_to`/`take_off` guarded in the base class, fail-closed without home | Manual commands inside the envelope are, by design, allowed |
| T11 | **Silent clipping hides a bad plan** | Speed above the limit is rejected, not clipped; the executor uses `min(configured, approved)` only as a second line | n/a |
| T12 | **Configuration tampering** (envelope loosened) | Envelope fingerprint is part of the hash: tightening or loosening after approval invalidates it | Whoever controls the environment/file can weaken limits for future missions |

## Framework mapping

| Framework item | Where it appears |
|---|---|
| OWASP LLM01:2025 Prompt Injection | T2, T3, T4 |
| OWASP LLM05:2025 Improper Output Handling | The original defect: LLM-produced mission JSON flowed to execution after only advisory checks; fixed by the envelope plus strict schemas |
| OWASP LLM06:2025 Excessive Agency | T1, T5, T8: the planner could, through an advisory-only path, cause an executed flight without a deterministic limit or human decision |
| MITRE ATLAS AML.T0051 LLM Prompt Injection (.000 Direct, .001 Indirect) | T2, T3, T4 |
| ATLAS AML.T0053 AI Agent Tool Invocation | T5: planner tools (`finalize_mission` persists plans) and the path from plan to controller |
| ATLAS AML.T0054 LLM Jailbreak | T1, T2: the plain-order vector does not need one; a jailbroken model is the T5 case |
| ATLAS AML.T0080 AI Agent Context Poisoning | T3, T4 if an LLM later consumes reports or video text |
| ATLAS mitigations AML.M0020 Generative AI Guardrails, AML.M0026 / M0028 Privileged AI Agent / Agent Tools Permissions Configuration, AML.M0029 Human In-the-Loop for AI Agent Actions, AML.M0033 Input and Output Validation for AI Agent Components | Strict schemas (M0033, M0020 as mitigation), least privilege for tools (M0026/M0028), binding approval (M0029) |

Identifiers are those of the versions above; re-check before citing against a newer release.
