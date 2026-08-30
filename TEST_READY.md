# Test Suite Ready: LangGraph Orchestrator (Milestone 4)

**Status:** Ready  
**Date:** 2026-08-30  
**Test Suite Path:** `/home/rhyme/repo/arc/orchestrator/tests/test_orchestrator.py`  
**Test Fixtures Path:** `/home/rhyme/repo/arc/orchestrator/tests/conftest.py`  
**Execution Command:** `/home/rhyme/repo/arc/venv/bin/pytest orchestrator/tests/test_orchestrator.py -v`  

---

## 1. Test Architecture & Coverage Summary

The acceptance test suite for Milestone 4 (LangGraph Orchestrator) is structured into 4 comprehensive tiers comprising **60 individual test cases**:

| Tier | Focus | Coverage Requirements | Tests Implemented | Pass / Ready Status |
|---|---|---|:---:|:---:|
| **Tier 1** | Feature Coverage | ≥5 tests per feature (F1 - F5) | 25 tests | Ready |
| **Tier 2** | Boundary & Corner Cases | ≥5 tests per boundary category | 25 tests | Ready |
| **Tier 3** | Cross-Feature Interactions | Interleaved ReAct + MCP + HITL | 5 tests | Ready |
| **Tier 4** | Real-World Application Scenarios | End-to-end benchmark on `dummy_code.py` | 5 scenarios | Ready |
| **Total** | Full Acceptance Suite | Full Requirement & Contract Coverage | **60 tests** | **READY** |

---

## 2. Test Tier Breakdown

### Tier 1: Feature Coverage (25 Tests)
- **Feature 1: ReAct State Machine (R1)**
  - `test_tier1_f1_agent_state_initialization`: Validates `AgentState` schema, typed fields, message history, memory dictionary, and iteration count initialization.
  - `test_tier1_f1_state_graph_compilation`: Validates compilation of `StateGraph` into executable `CompiledStateGraph` app.
  - `test_tier1_f1_state_message_reducer`: Validates `add_messages` reducer semantics when appending `HumanMessage` and `AIMessage`.
  - `test_tier1_f1_iteration_counter_guard`: Validates execution guard against infinite loops when `max_iterations` threshold is exceeded.
  - `test_tier1_f1_reasoner_node_execution`: Validates reasoner node state transformation and reasoning generation.
- **Feature 2: Dynamic MCP Tool Integration (R2)**
  - `test_tier1_f2_mcp_client_manager_default_params`: Validates parameter generation for AST and Sandbox servers.
  - `test_tier1_f2_mcp_client_manager_initialization`: Validates manager lifecycle without hardcoded tool schemas.
  - `test_tier1_f2_dynamic_tool_discovery_and_conversion`: Validates dynamic conversion of MCP tools to LangChain `StructuredTool` objects.
  - `test_tier1_f2_ast_tool_execution_dummy_code`: Validates live AST tools (`function_signature`, `class_methods`, `extract_block`) against `dummy_code.py`.
  - `test_tier1_f2_sandbox_tool_execution`: Validates sandbox execution helpers (`command_runner`, `reset_sandbox`).
- **Feature 3: HITL Governance Breakpoint (R3)**
  - `test_tier1_f3_hitl_interrupt_trigger`: Validates that state machine triggers LangGraph `interrupt()` when patch is drafted and tested.
  - `test_tier1_f3_hitl_resume_approval`: Validates graph resumption via `Command(resume={"approved": True})` transitioning to completed.
  - `test_tier1_f3_hitl_resume_rejection`: Validates graph resumption via `Command(resume={"approved": False, "feedback": ...})` routing back to reasoner.
  - `test_tier1_f3_hitl_gate_node_direct_call`: Validates direct invocation and signature of `hitl_gate_node`.
  - `test_tier1_f3_hitl_checkpointer_state_persistence`: Validates that `MemorySaver` preserves thread state across suspension.
- **Feature 4: Multi-Model Routing (R4)**
  - `test_tier1_f4_openrouter_llm_factory`: Validates `create_openrouter_llm` setting `base_url="https://openrouter.ai/api/v1"` with `ChatOpenAI`.
  - `test_tier1_f4_openrouter_custom_models`: Validates routing across various model identifiers (Claude 3.5 Sonnet, GPT-4o, Llama 3.1, DeepSeek).
  - `test_tier1_f4_mock_llm_deterministic_mode`: Validates offline demo mock LLM delivering deterministic test sequences.
  - `test_tier1_f4_llm_tool_binding`: Validates `.bind_tools()` binding dynamically discovered MCP tools to LLM.
  - `test_tier1_f4_openrouter_api_key_resolution`: Validates API key resolution from environment variable `OPENROUTER_API_KEY` or direct parameters.
- **Feature 5: Bug Repair on `dummy_code.py` (Acceptance Criteria)**
  - `test_tier1_f5_dummy_code_bug_identification`: Validates AST extraction pinpointing `return False` in `PaymentGateway.refund_payment`.
  - `test_tier1_f5_dummy_code_patch_logic`: Validates patching logic correcting `return False` to `return True`.
  - `test_tier1_f5_dummy_code_class_methods_discovery`: Validates AST class methods discovery on `PaymentGateway`.
  - `test_tier1_f5_dummy_code_calculate_tax_unaffected`: Validates patch preserves other functions (`calculate_tax`).
  - `test_tier1_f5_dummy_code_patch_record_structure`: Validates `PatchRecord` schema compliance.

---

### Tier 2: Boundary & Corner Cases (25 Tests)
- **Category 1: State & Message Boundaries**: Empty messages list handling, zero max iterations guard, empty history handling, large memory dictionaries, prompt special escaping and characters.
- **Category 2: MCP Tool Errors**: Unregistered tool invocation handling, AST invalid line range handling, AST non-existent function name handling, AST non-existent file path handling, sandbox non-zero exit code capture.
- **Category 3: HITL Governance Edge Cases**: String resumption payloads, empty dictionary resumption payloads, multiple consecutive rejections with distinct feedback, non-interrupt resumption handling, pending patch reset on rejection.
- **Category 4: LLM & Routing Edge Cases**: Missing API key demo fallback, empty response list handling, multi-tool parallel calls, temperature settings boundary validation, tool exception isolation.
- **Category 5: Bug Repair Edge Cases**: Non-existent target file path handling, empty patch content handling, corrupted syntax error detection, unknown class name error handling, patch idempotency verification.

---

### Tier 3: Cross-Feature Interactions (5 Tests)
- `test_tier3_react_loop_ast_and_sandbox_interaction`: Tests interleaved AST code inspection and sandbox patch execution in continuous ReAct cycle.
- `test_tier3_sandbox_test_failure_to_error_history_to_replan`: Tests sandbox test failure propagation into `error_history` triggering reasoning self-correction.
- `test_tier3_hitl_rejection_cycle_and_second_approval`: Tests full multi-turn cycle: Pause -> Reject -> Reasoner adapts -> Pause -> Approve -> Complete.
- `test_tier3_thread_isolation_concurrent_sessions`: Tests checkpointer isolation between concurrent thread IDs.
- `test_tier3_mcp_client_session_reconnect_resilience`: Tests MCP client session manager re-initialization and clean session state.

---

### Tier 4: Real-World Scenarios (5 Scenarios)
- **Scenario 1 (`test_tier4_scenario_1_full_payment_gateway_bug_repair`)**: Complete end-to-end benchmark on `PaymentGateway.refund_payment` in `dummy_code.py`. Agent discovers bug, drafts patch, runs verification tests, pauses at HITL `interrupt()` checkpoint, user inspects and approves, and agent successfully completes.
- **Scenario 2 (`test_tier4_scenario_2_orchestrator_agent_runner_facade`)**: Tests high-level `OrchestratorAgent` facade execution.
- **Scenario 3 (`test_tier4_scenario_3_multi_turn_self_repair_loop`)**: Tests iterative repair cycle where initial patch fails tests and agent automatically generates passing patch before HITL pause.
- **Scenario 4 (`test_tier4_scenario_4_human_rejection_and_reprompt_recovery`)**: Tests human rejection requesting docstring and agent updating patch to satisfy review.
- **Scenario 5 (`test_tier4_scenario_5_openrouter_demo_fallback_execution`)**: Tests offline demo mode fallback execution.

---

## 3. How to Run

Execute the full acceptance test suite using pytest:

```bash
/home/rhyme/repo/arc/venv/bin/pytest orchestrator/tests/test_orchestrator.py -v
```

To run a specific tier:

```bash
# Run Tier 1 only:
/home/rhyme/repo/arc/venv/bin/pytest orchestrator/tests/test_orchestrator.py -k "TestTier1" -v

# Run Tier 4 Real-World Scenarios only:
/home/rhyme/repo/arc/venv/bin/pytest orchestrator/tests/test_orchestrator.py -k "TestTier4" -v
```
