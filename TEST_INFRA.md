# E2E Test Infra: LangGraph Orchestrator (Milestone 4)

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation internals.
- Methodology: Category-Partition + BVA + Pairwise + Workload Testing.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | ReAct State Machine | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 2 | Dynamic MCP Tool Integration | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 3 | HITL Governance Breakpoint | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 4 | Multi-Model Routing | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 5 | Bug Repair on dummy_code.py | ORIGINAL_REQUEST §Acceptance Criteria | 5 | 5 | ✓ |

## Test Architecture
- Test runner: `pytest orchestrator/tests/test_orchestrator.py -v`
- Test case format: Pytest test cases verifying LangGraph graph compilation, MCP tool discovery, HITL pause on state machine, and bug fix assertion on `dummy_code.py`.
- Directory layout: `orchestrator/tests/`

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full end-to-end bug repair cycle on `dummy_code.py` with MCP tools and HITL pause | F1, F2, F3, F4, F5 | High |
| 2 | Dynamic MCP tool loading across AST and Sandbox servers without hardcoding | F2, F5 | Medium |
| 3 | Human rejection / approval resumption loop | F1, F3 | Medium |
| 4 | Multi-turn ReAct reasoning loop with error correction | F1, F2 | High |
| 5 | OpenRouter routing configuration and fallback demo behavior | F4 | Medium |

## Coverage Thresholds
- Tier 1: ≥5 per feature
- Tier 2: ≥5 per feature (where boundaries exist)
- Tier 3: pairwise coverage of major feature interactions
- Tier 4: ≥5 realistic application scenarios
