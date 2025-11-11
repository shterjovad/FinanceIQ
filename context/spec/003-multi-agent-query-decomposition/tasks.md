# Task List: Multi-Agent Query Decomposition

**Specification**: `context/spec/003-multi-agent-query-decomposition/`
**Target**: Implement LangGraph-based multi-agent orchestration for complex query handling
**Status**: Ready for Implementation

---

## Vertical Slicing Strategy

Each slice builds on the previous and leaves the application **runnable and testable**. We maintain the Phase 1 pattern of end-to-end increments.

---

## Tasks

### Slice 1: LangGraph Setup & Basic State Machine
**Goal**: Set up LangGraph infrastructure and create simplest possible workflow that routes all queries through the system.

- [ ] **Slice 1.1: Add LangGraph Dependencies**
  - [ ] Add to `pyproject.toml`: `langgraph>=0.2.0`, `langchain-core>=0.3.0`
  - [ ] Run `uv sync` to install dependencies
  - [ ] Verify imports work: `from langgraph.graph import StateGraph`
  - [ ] Test in Python REPL

- [ ] **Slice 1.2: Create Agent Module Structure**
  - [ ] Create `src/agents/__init__.py`
  - [ ] Create `src/agents/models.py` with `AgentState` TypedDict
  - [ ] Include all fields: original_question, query_type, sub_queries, sub_results, final_answer, reasoning_steps, etc.
  - [ ] Add docstrings explaining each field
  - [ ] Verify imports: `from src.agents.models import AgentState`

- [ ] **Slice 1.3: Create Minimal Workflow (Pass-Through)**
  - [ ] Create `src/agents/workflow.py`
  - [ ] Implement simplest workflow: Input → Output (no actual agents yet)
  - [ ] Define `create_agent_workflow()` function
  - [ ] Create StateGraph with single "passthrough" node
  - [ ] Test: Pass question in, get question back out
  - [ ] Verify LangGraph state management works

- [ ] **Slice 1.4: Add Configuration**
  - [ ] Update `src/config/settings.py` with agent settings
  - [ ] Add `USE_AGENTS: bool = False` (feature flag, default off)
  - [ ] Add `AGENT_ROUTER_MODEL`, `AGENT_DECOMPOSER_MODEL`, `AGENT_SYNTHESIZER_MODEL`
  - [ ] Add `MAX_SUB_QUERIES: int = 5`
  - [ ] Update `.env.example`
  - [ ] Test settings load correctly

**Runnable Outcome**: LangGraph installed, basic workflow exists (pass-through), no errors when importing agents module.

---

### Slice 2: Query Router Agent (Simple vs Complex Classification)
**Goal**: Implement first real agent that classifies queries, with fallback to existing RAG for all queries.

- [ ] **Slice 2.1: Implement Query Router Agent**
  - [ ] Create `src/agents/router.py`
  - [ ] Implement `query_router_agent(state: AgentState) -> AgentState`
  - [ ] Use GPT-3.5-turbo for classification (cheaper, faster)
  - [ ] Implement few-shot prompt with examples
  - [ ] Return JSON: `{"type": "simple|complex", "reasoning": "..."}`
  - [ ] Update state with `query_type` and `complexity_reasoning`
  - [ ] Add error handling and retry logic
  - [ ] Add logging

- [ ] **Slice 2.2: Unit Tests for Router**
  - [ ] Create `tests/agents/test_router.py`
  - [ ] Test simple query classification: "What was total revenue?"
  - [ ] Test complex query classification: "How did revenue change Q1 to Q2 and why?"
  - [ ] Test edge cases: empty query, very long query
  - [ ] Mock LLM responses to test parsing
  - [ ] Run tests: `pytest tests/agents/test_router.py -v`

- [ ] **Slice 2.3: Integrate Router into Workflow**
  - [ ] Update `workflow.py` to add router node
  - [ ] Add conditional edge: simple → fallback to existing RAG, complex → (placeholder for now)
  - [ ] For now, route ALL queries to existing RAG regardless of classification
  - [ ] Test: Run query through workflow, verify it reaches RAG engine
  - [ ] Verify classification is logged but not yet used

- [ ] **Slice 2.4: Add Feature Flag Integration**
  - [ ] Update `RAGService` to accept `use_agents: bool` parameter
  - [ ] If `use_agents=False`: direct to existing query engine (Phase 1 behavior)
  - [ ] If `use_agents=True`: route through agent workflow (Phase 2 behavior)
  - [ ] Test both paths work correctly
  - [ ] Verify no performance regression when `use_agents=False`

**Runnable Outcome**: Queries can be classified as simple/complex, but all still routed to existing RAG. Feature flag allows toggling between Phase 1 and Phase 2 behavior.

---

### Slice 3: Query Decomposer Agent
**Goal**: Implement agent that breaks complex queries into sub-queries.

- [ ] **Slice 3.1: Implement Query Decomposer Agent**
  - [ ] Create `src/agents/decomposer.py`
  - [ ] Implement `query_decomposer_agent(state: AgentState) -> AgentState`
  - [ ] Use GPT-4 for decomposition (better reasoning)
  - [ ] Implement chain-of-thought prompting
  - [ ] Return JSON: `{"sub_queries": [...], "execution_order": "parallel|sequential", "reasoning": "..."}`
  - [ ] Limit to MAX_SUB_QUERIES (default 5)
  - [ ] Update state with `sub_queries` and `execution_order`
  - [ ] Add to `reasoning_steps` for transparency
  - [ ] Add error handling and logging

- [ ] **Slice 3.2: Unit Tests for Decomposer**
  - [ ] Create `tests/agents/test_decomposer.py`
  - [ ] Test decomposition of complex query: "How did iPhone sales compare Q3 vs Q4?"
  - [ ] Verify sub-queries are well-formed
  - [ ] Test max sub-queries limit (should stop at 5)
  - [ ] Test execution order determination (parallel vs sequential)
  - [ ] Mock LLM responses
  - [ ] Run tests: `pytest tests/agents/test_decomposer.py -v`

- [ ] **Slice 3.3: Integrate Decomposer into Workflow**
  - [ ] Update `workflow.py` to add decomposer node
  - [ ] Add edge: router (if complex) → decomposer
  - [ ] For now, decomposer outputs sub-queries but doesn't execute them
  - [ ] Log sub-queries but still route to direct RAG query
  - [ ] Test: Complex query gets decomposed, logs show sub-queries

- [ ] **Slice 3.4: Add Decomposition Preview to UI (Optional)**
  - [ ] In chat component, if agents enabled and query is complex
  - [ ] Show info box: "🧠 Analyzing complex question..."
  - [ ] Display sub-queries in expandable section (before execution)
  - [ ] Test with real UI

**Runnable Outcome**: Complex queries are decomposed into sub-queries and logged. Sub-queries not yet executed, but user can see the decomposition plan.

---

### Slice 4: Sub-Query Executor
**Goal**: Execute sub-queries using existing RAG system, aggregate results.

- [ ] **Slice 4.1: Implement Sub-Query Executor**
  - [ ] Create `src/agents/executor.py`
  - [ ] Implement `sub_query_executor(state: AgentState) -> AgentState`
  - [ ] Accept `rag_query_engine` as dependency (dependency injection)
  - [ ] Execute each sub-query through existing `RAGQueryEngine.query()`
  - [ ] Handle parallel execution (ThreadPoolExecutor, max_workers=3)
  - [ ] Handle sequential execution (loop)
  - [ ] Store results in `state["sub_results"]`
  - [ ] Add error handling for individual sub-query failures
  - [ ] Add progress tracking

- [ ] **Slice 4.2: Unit Tests for Executor**
  - [ ] Create `tests/agents/test_executor.py`
  - [ ] Mock RAGQueryEngine
  - [ ] Test parallel execution of 3 sub-queries
  - [ ] Test sequential execution
  - [ ] Test partial failure (1 of 3 sub-queries fails)
  - [ ] Test retry logic
  - [ ] Run tests: `pytest tests/agents/test_executor.py -v`

- [ ] **Slice 4.3: Integrate Executor into Workflow**
  - [ ] Update `workflow.py` to add executor node
  - [ ] Add edge: decomposer → executor
  - [ ] Pass `rag_query_engine` to executor via workflow config
  - [ ] Test: Complex query gets decomposed → sub-queries executed → results stored
  - [ ] Verify all sub-results are QueryResult objects

- [ ] **Slice 4.4: Display Sub-Query Results in UI**
  - [ ] In reasoning steps display, show each sub-query result
  - [ ] Format: "Sub-Query 1: [question] → Answer: [answer] → Sources: [page numbers]"
  - [ ] Show execution progress: "Executing sub-query 2 of 3..."
  - [ ] Test with real query

**Runnable Outcome**: Complex queries are decomposed and each sub-query is executed. Results visible in reasoning steps. No final synthesis yet (shows all sub-answers separately).

---

### Slice 5: Answer Synthesis Agent
**Goal**: Combine sub-answers into coherent final response.

- [ ] **Slice 5.1: Implement Answer Synthesis Agent**
  - [ ] Create `src/agents/synthesizer.py`
  - [ ] Implement `answer_synthesis_agent(state: AgentState) -> AgentState`
  - [ ] Use GPT-4 for synthesis (quality matters)
  - [ ] Build context from all sub-results
  - [ ] Prompt: synthesize comprehensive answer addressing original question
  - [ ] Aggregate all sources from sub-results
  - [ ] Update state with `final_answer` and `all_sources`
  - [ ] Add to reasoning steps
  - [ ] Add error handling

- [ ] **Slice 5.2: Unit Tests for Synthesizer**
  - [ ] Create `tests/agents/test_synthesizer.py`
  - [ ] Mock sub-results with 3 different answers
  - [ ] Test synthesis produces coherent response
  - [ ] Test all sources are aggregated
  - [ ] Test handling of conflicting sub-answers
  - [ ] Mock LLM
  - [ ] Run tests: `pytest tests/agents/test_synthesizer.py -v`

- [ ] **Slice 5.3: Integrate Synthesizer into Workflow**
  - [ ] Update `workflow.py` to add synthesizer node
  - [ ] Add edge: executor → synthesizer → END
  - [ ] Test: Full workflow end-to-end
  - [ ] Verify final_answer addresses original question
  - [ ] Verify all sources preserved

- [ ] **Slice 5.4: Update Chat UI to Display Final Answer**
  - [ ] Display synthesized final answer (not individual sub-answers)
  - [ ] Show all aggregated sources
  - [ ] In reasoning steps, show synthesis step
  - [ ] Test: Ask complex question, get comprehensive answer
  - [ ] Compare quality to Phase 1 direct query

**Runnable Outcome**: Full agent workflow functional. Complex queries decomposed → executed → synthesized. User gets comprehensive answer with complete source citations.

---

### Slice 6: Agent Orchestration Service
**Goal**: Clean service layer wrapping the workflow, integrated with existing RAGService.

- [ ] **Slice 6.1: Implement AgentOrchestrationService**
  - [ ] Create `src/agents/service.py`
  - [ ] Implement `AgentOrchestrationService` class
  - [ ] Constructor accepts `rag_query_engine` dependency
  - [ ] Implement `process_query(question: str) -> QueryResult`
  - [ ] Initialize LangGraph workflow
  - [ ] Execute workflow with question
  - [ ] Convert agent state to QueryResult
  - [ ] Handle simple query bypass (route directly to RAG)
  - [ ] Add comprehensive logging
  - [ ] Add error handling

- [ ] **Slice 6.2: Integration Tests for Service**
  - [ ] Create `tests/agents/test_service.py`
  - [ ] Test simple query (bypasses agents)
  - [ ] Test complex query (full workflow)
  - [ ] Test with real RAG components (not mocked)
  - [ ] Verify QueryResult structure matches Phase 1
  - [ ] Run tests: `pytest tests/agents/test_service.py -v`

- [ ] **Slice 6.3: Integrate with RAGService**
  - [ ] Update `src/rag/service.py`
  - [ ] Add `use_agents: bool` parameter to constructor
  - [ ] Initialize `AgentOrchestrationService` if `use_agents=True`
  - [ ] Update `query()` method to route through agents or direct
  - [ ] Maintain backward compatibility (default `use_agents=False`)
  - [ ] Test both paths

- [ ] **Slice 6.4: Update Main App**
  - [ ] Update `src/ui/app.py`
  - [ ] Read `USE_AGENTS` from settings
  - [ ] Pass to `RAGService` constructor
  - [ ] Add toggle in UI sidebar: "Enable Multi-Agent Query Processing"
  - [ ] Store in session state
  - [ ] Test toggling on/off

**Runnable Outcome**: Clean service architecture. Feature flag controls Phase 1 vs Phase 2 behavior. Users can toggle agents on/off in UI.

---

### Slice 7: Testing, Performance & Polish
**Goal**: Comprehensive testing, performance validation, documentation.

- [ ] **Slice 7.1: End-to-End Integration Tests**
  - [ ] Create `tests/integration/test_agents_e2e.py`
  - [ ] Test with real Apple 10-K document
  - [ ] Test complex queries:
    - "How did iPhone sales compare Q3 vs Q4 and what were the reasons?"
    - "What are the top 3 revenue drivers and how did they change?"
  - [ ] Verify decomposition quality
  - [ ] Verify final answer quality
  - [ ] Verify sources are accurate
  - [ ] Run tests: `pytest tests/integration/test_agents_e2e.py -v`

- [ ] **Slice 7.2: Performance Benchmarking**
  - [ ] Measure simple query response time (should match Phase 1: 3-5s)
  - [ ] Measure complex query response time (target: <15s for 3 sub-queries)
  - [ ] Measure query router latency (target: <500ms)
  - [ ] Measure per-agent execution time
  - [ ] Log all metrics
  - [ ] Optimize if targets not met

- [ ] **Slice 7.3: Code Quality Checks**
  - [ ] Run ruff linter: `ruff check src/agents/`
  - [ ] Run mypy type checker: `mypy src/agents/ --strict`
  - [ ] Fix any errors
  - [ ] Verify 100% type hint coverage
  - [ ] Run full test suite: `pytest tests/ -v`

- [ ] **Slice 7.4: Manual Testing**
  - [ ] Test with multiple complex queries
  - [ ] Verify reasoning steps display correctly
  - [ ] Test edge cases: very complex queries, ambiguous queries
  - [ ] Test error handling: LLM failures, timeout scenarios
  - [ ] Document any issues found

- [ ] **Slice 7.5: Documentation Updates**
  - [ ] Update `README.md` with Phase 2 features
  - [ ] Add example complex queries
  - [ ] Update architecture description
  - [ ] Document agent toggle in UI
  - [ ] Add LangGraph to tech stack

- [ ] **Slice 7.6: Update Roadmap**
  - [ ] Mark Phase 2 as complete in `roadmap.md`
  - [ ] Update success metrics
  - [ ] Document lessons learned

**Runnable Outcome**: Fully tested Phase 2 implementation. Performance validated. Documentation complete. System ready for Phase 3 (polish) or production use.

---

## Summary

**Total Slices**: 7
**Total Sub-tasks**: 45

Each slice is designed to be **independently runnable and testable**. The system maintains Phase 1 functionality throughout (feature flag allows toggling agents on/off).

**Key Principles Applied**:
- ✅ Vertical slicing (end-to-end increments)
- ✅ Runnable after each slice
- ✅ User-visible progress
- ✅ Incremental complexity
- ✅ Test as you go
- ✅ Backward compatibility

**Estimated Effort**: ~2-3 days total development time

---

## Next Steps

Ready to start Slice 1: LangGraph Setup & Basic State Machine?
