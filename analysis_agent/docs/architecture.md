# Vigilant AI - System Architecture

## Overview

Vigilant AI is a sophisticated multi-agent architecture designed for intelligent test verification through video analysis. The system combines advanced computer vision, OCR technology, and Large Language Models (LLMs) to verify test execution against expected outcomes by analyzing video recordings of test runs.

The architecture follows a modular, agent-based design pattern where specialized agents collaborate under an orchestrator to perform complex verification tasks. This approach enables:

- **Efficient LLM Usage**: Minimizing API calls through smart batching and triage
- **Comprehensive Analysis**: Combining visual, textual, and temporal evidence
- **Scalable Verification**: Handling tests of varying complexity with adaptive strategies
- **Multi-Format Reporting**: Generating actionable reports in JSON, HTML, and Markdown

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INPUT / OUTPUT LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Planning Log    │  │ Test Output     │  │ Video           │              │
│  │ (JSON)          │  │ (XML)           │  │ Recording       │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                    │                       │
│           └────────────────────┼────────────────────┘                       │
│                                ▼                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                         USER INTERFACE LAYER                                │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐         │
│  │   Streamlit UI              │    │   FastAPI Backend           │         │
│  │   (main_ui.py)              │    │   (api/main.py)             │         │
│  └──────────────┬──────────────┘    └──────────────┬──────────────┘         │
│                 │                                  │                        │
│                 └──────────────┬───────────────────┘                        │
│                                ▼                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                        ORCHESTRATION LAYER                                  │
│                 ┌─────────────────────────────┐                             │
│                 │     OrchestratorAgent       │                             │
│                 │     (orchestrator.py)       │                             │
│                 └──────────────┬──────────────┘                             │
│                                │                                            │
│          ┌─────────────┬───────┴───────┬─────────────┐                      │
│          ▼             ▼               ▼             ▼                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                       SPECIALIZED AGENTS LAYER                              │
│  ┌─────────────┐ ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐    │
│  │ Planning    │ │ Comprehensive   │ │ OCR         │ │ Verification    │    │
│  │ Agent       │ │ VisionAgent     │ │ Agent       │ │ Agent           │    │
│  └──────┬──────┘ └────────┬────────┘ └──────┬──────┘ └────────┬────────┘    │
│         │                 │                 │                 │             │
│         └─────────────────┴─────────────────┴─────────────────┘             │
│                                │                                            │
│                                ▼                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                       CORE INFRASTRUCTURE LAYER                             │
│                 ┌─────────────────────────────┐                             │
│                 │        BaseAgent            │                             │
│                 └──────────────┬──────────────┘                             │
│                                │                                            │
│                                ▼                                            │
│                 ┌─────────────────────────────┐                             │
│                 │   LLMFactory                │                             │
│                 │   (Gemini/CLI/OpenSource)   │                             │
│                 └──────────────┬──────────────┘                             │
│                                │                                            │
│                                ▼                                            │
│                 ┌─────────────────────────────┐                             │
│                 │      Pydantic Models        │                             │
│                 └─────────────────────────────┘                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                              OUTPUT                                         │
│                 ┌─────────────────────────────┐                             │
│                 │   Reports: JSON/HTML/MD     │                             │
│                 └─────────────────────────────┘                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| **User Interface** | Streamlit UI | Interactive web interface for file upload and report viewing |
| **User Interface** | FastAPI Backend | RESTful API for programmatic access and integrations |
| **Orchestration** | OrchestratorAgent | Coordinates all agents, manages workflow, handles progress reporting |
| **Specialized Agents** | PlanningAgent | Analyzes test complexity, creates verification strategies |
| **Specialized Agents** | ComprehensiveVisionAgent | Performs single-pass video analysis with LLM |
| **Specialized Agents** | OCRAgent | Extracts text from video frames using EasyOCR |
| **Specialized Agents** | VerificationAgent | Matches evidence to test steps, determines pass/fail status |
| **Core Infrastructure** | BaseAgent | Abstract base class with shared agent functionality |
| **Core Infrastructure** | LLMFactory | Factory pattern for LLM provider selection |
| **Core Infrastructure** | Pydantic Models | Type-safe data models for all system entities |

---

## Process Flow

The verification process follows a three-stage pipeline: **Input Ingestion → Step Comparison → Report Generation**

### 3.1 Input Ingestion Process

```
┌──────────────────────────┐      ┌──────────────────────────┐      ┌──────────────────────────┐
│   Planning Log JSON      │      │   Test Output XML        │      │   Video Recording        │
│   (test steps)           │      │   (JUnit)                │      │   (MP4/MOV)              │
└───────────┬──────────────┘      └───────────┬──────────────┘      └───────────┬──────────────┘
            │                                 │                                 │
            ▼                                 ▼                                 ▼
┌──────────────────────────┐      ┌──────────────────────────┐      ┌──────────────────────────┐
│   PlanningLogParser      │      │   TestOutputParser       │      │   Temporary Storage      │
└───────────┬──────────────┘      └───────────┬──────────────┘      └───────────┬──────────────┘
            │                                 │                                 │
            ▼                                 ▼                                 ▼
┌──────────────────────────┐      ┌──────────────────────────┐      ┌──────────────────────────┐
│   PlanningLog Model      │      │   TestOutput Model       │      │   Video Path             │
└───────────┬──────────────┘      └───────────┬──────────────┘      └───────────┬──────────────┘
            │                                 │                                 │
            └─────────────────────────────────┼─────────────────────────────────┘
                                              │
                                              ▼
                          ┌──────────────────────────────────────────┐
                          │  OrchestratorAgent.execute_verification  │
                          └──────────────────────────────────────────┘
```

#### Input Specifications

**Planning Log (JSON)**
- Contains `planner_agent` messages with structured test step information
- Each step includes `next_step` (detailed action) and `next_step_summary` (brief description)
- Steps are numbered sequentially for temporal ordering
- Example fields: `step_number`, `description`, `action`, `expected_outcome`

**Test Output (XML)**
- JUnit-style XML format for compatibility with CI/CD systems
- Contains pass/fail status for each test case
- Includes execution timestamps and error messages (if any)
- Parsed into structured `TestOutput` model for processing

**Video Recording**
- Supported formats: MP4, MOV, WebM
- Stored temporarily for frame extraction
- Deleted after processing to conserve storage
- Frame rate and resolution automatically detected

---

### 3.2 Step Comparison Process (7-Phase Workflow)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    7-PHASE VERIFICATION WORKFLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 1: Planning (0-5%)                                                   │
│  ├── Analyze test complexity                                                │
│  └── Create VerificationStrategy                                            │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 2: Frame Extraction (5-15%)                                          │
│  ├── Extract frames at 0.5s interval                                        │
│  └── Apply max_frames limit                                                 │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 3: Key Frame Selection (15-20%)                                      │
│  ├── Strategic sampling algorithm                                           │
│  └── First + Last + Evenly distributed                                      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 4: OCR Analysis (20-30%)                                             │
│  ├── EasyOCR on key frames                                                  │
│  └── Extract text with confidence scores                                    │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 5: Vision Analysis (30-60%)                                          │
│  ├── SINGLE LLM call with ALL frames                                        │
│  ├── Generate VideoTimeline                                                 │
│  └── Extract TimelineEvents                                                 │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 6: Smart Verification (60-95%)                                       │
│  ├── Gather evidence per step                                               │
│  ├── Smart triage decision                                                  │
│  │   ├── Code-based verification                                            │
│  │   └── LLM semantic verification                                          │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 7: Report Generation (95-100%)                                       │
│  ├── Calculate pass/fail/uncertain                                          │
│  └── Generate multi-format reports                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Phase Details

**Phase 1: Planning (0-5%)**
- Analyzes the complexity of the test based on number of steps and action types
- Creates a `VerificationStrategy` that determines resource allocation
- Sets parameters like `max_frames`, sampling rate, and batch sizes
- Identifies assertion-heavy tests that will need more LLM verification

**Phase 2: Frame Extraction (5-15%)**
- Extracts video frames at configurable intervals (default: 0.5 seconds)
- Applies `max_frames` limit to prevent memory issues with long videos
- Maintains frame metadata: timestamp, frame number, source video info
- Uses OpenCV for efficient frame extraction

**Phase 3: Key Frame Selection (15-20%)**
- Applies strategic sampling algorithm to select representative frames
- Selection strategy: **First frame + Last frame + Evenly distributed middle frames**
- Reduces frame count while preserving critical moments
- Typical reduction: 100+ frames → 10-20 key frames

**Phase 4: OCR Analysis (20-30%)**
- Runs EasyOCR on each key frame to extract visible text
- Captures UI element labels, error messages, form data, etc.
- Each extraction includes confidence scores for reliability assessment
- Aggregates text per frame with position information

**Phase 5: Vision Analysis (30-60%)**
- **CRITICAL**: Sends ALL key frames in a SINGLE LLM call
- LLM generates a comprehensive `VideoTimeline` with temporal events
- Each `TimelineEvent` captures: timestamp, UI elements, visible text, actions observed
- Creates a narrative description of the entire test flow
- This single-pass approach is 10-100x more efficient than per-frame analysis

**Phase 6: Smart Verification (60-95%)**
- For each test step, gathers relevant evidence from the `VideoTimeline`
- Applies **smart triage** to decide verification approach:
  - **Code-based**: Direct string matching for high-confidence simple steps
  - **LLM-based**: Semantic verification for complex assertions and borderline cases
- Respects temporal ordering: evidence for step N must come after step N-1
- Uses batch mode for efficiency when many steps need LLM verification

**Phase 7: Report Generation (95-100%)**
- Calculates final statistics: pass rate, deviation count, confidence scores
- Generates reports in three formats: JSON, HTML, Markdown
- Includes detailed evidence and reasoning for each verification result
- HTML reports feature styled gradients and interactive elements

---

### 3.3 Report Generation

```
                                    ┌────────────────────────────────┐
                                    │  JSON Report                   │
                               ┌───►│  (Machine-readable)            │
                               │    └────────────────────────────────┘
┌────────────────────────┐     │
│  DeviationReport       │     │    ┌────────────────────────────────┐
│  (All results)         │─────┼───►│  HTML Report                   │
└────────────────────────┘     │    │  (Styled)                      │
            │                  │    └────────────────────────────────┘
            ▼                  │
┌────────────────────────┐     │    ┌────────────────────────────────┐
│  ReportGenerator       │─────┴───►│  Markdown Report               │
└────────────────────────┘          │  (Docs)                        │
                                    └────────────────────────────────┘
```

#### Status Classification

| Status | Symbol | Definition | Typical Confidence |
|--------|--------|------------|-------------------|
| **OBSERVED** | ✅ | Step verified successfully with high confidence | ≥ 0.7 |
| **DEVIATION** | ❌ | Step contradicted by video evidence, or expected action not found | Any confidence with negative evidence |
| **UNCERTAIN** | ⚠️ | Insufficient evidence to confirm or deny step execution | 0.3 - 0.7 |

#### Report Format Details

**JSON Report**
- Machine-readable format for CI/CD integration
- Complete data model serialization
- Includes all evidence and metadata
- Suitable for programmatic analysis

**HTML Report**
- Styled presentation with gradient colors
- Status indicators with icons
- Collapsible evidence sections
- Print-friendly layout

**Markdown Report**
- Documentation-friendly format
- Easy to include in repositories
- Compatible with GitHub/GitLab rendering
- Suitable for PR comments and issue tracking

---

## Smart Triage Logic

The Smart Triage system intelligently decides when to use expensive LLM verification versus efficient code-based matching:

| Condition | Verification Type | Reason |
|-----------|-------------------|--------|
| Assertion step (contains "assert", "verify", "validate") | LLM | Semantic understanding needed for assertion evaluation |
| Evidence contains "NOT visible", "NOT available" | LLM | Contradiction detection requires reasoning |
| Confidence 0.5 - 0.9 (borderline) | LLM | Needs semantic confirmation to resolve ambiguity |
| Filter/click/select interactions | LLM | UI state verification requires visual understanding |
| High confidence (≥0.9) simple steps | Code-based | Direct evidence match, no reasoning needed |
| < 5 steps needing LLM | Async per-step | Parallel processing for speed |
| ≥ 5 steps needing LLM | Batch mode | Single LLM call for efficiency |

### Triage Decision Flow

```
                        ┌──────────────────────────┐
                        │  Step Evidence Gathered  │
                        └────────────┬─────────────┘
                                     │
                                     ▼
                        ┌──────────────────────────┐
                        │  Confidence >= 0.9?      │
                        └────────────┬─────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │ Yes                             │ No
                    ▼                                 ▼
        ┌───────────────────────┐       ┌───────────────────────────┐
        │  Simple step?         │       │  Contains assertion       │
        └───────────┬───────────┘       │  keywords?                │
                    │                   └─────────────┬─────────────┘
        ┌───────────┴───────────┐                     │
        │ Yes               │ No         ┌────────────┴────────────┐
        ▼                   ▼            │ Yes                     │ No
┌─────────────────┐  ┌─────────────┐     ▼                         ▼
│  Code-based     │  │  LLM        │  ┌─────────────┐  ┌───────────────────────┐
│  Verification   │  │  Verification│  │  LLM        │  │  Negative indicators  │
└────────┬────────┘  └──────┬──────┘  │  Verification│  │  found?               │
         │                  │         └──────┬──────┘  └─────────────┬─────────┘
         │                  │                │                       │
         │                  │                │          ┌────────────┴────────────┐
         │                  │                │          │ Yes                     │ No
         │                  │                │          ▼                         ▼
         │                  │                │   ┌─────────────┐  ┌───────────────────────┐
         │                  │                │   │  LLM        │  │  Borderline           │
         │                  │                │   │  Verification│  │  confidence?          │
         │                  │                │   └──────┬──────┘  └─────────────┬─────────┘
         │                  │                │          │                       │
         │                  │                │          │          ┌────────────┴────────────┐
         │                  │                │          │          │ Yes                     │ No
         │                  │                │          │          ▼                         ▼
         │                  │                │          │   ┌─────────────┐        ┌─────────────────┐
         │                  │                │          │   │  LLM        │        │  Code-based     │
         │                  │                │          │   │  Verification│        │  Verification   │
         │                  │                │          │   └──────┬──────┘        └────────┬────────┘
         │                  │                │          │          │                        │
         │                  └────────────────┼──────────┴──────────┘                        │
         │                                   │                                              │
         │                                   ▼                                              │
         │                  ┌────────────────────────────┐                                  │
         │                  │  5+ steps pending?         │                                  │
         │                  └────────────┬───────────────┘                                  │
         │                               │                                                  │
         │              ┌────────────────┴────────────────┐                                 │
         │              │ Yes                             │ No                              │
         │              ▼                                 ▼                                 │
         │    ┌─────────────────────┐       ┌─────────────────────┐                         │
         │    │  Batch LLM Call     │       │  Async Per-Step     │                         │
         │    └──────────┬──────────┘       │  Call               │                         │
         │               │                  └──────────┬──────────┘                         │
         │               │                             │                                    │
         │               └──────────────┬──────────────┘                                    │
         │                              │                                                   │
         └──────────────────────────────┼───────────────────────────────────────────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │   Verification Result    │
                          └──────────────────────────┘
```

---

## Design Philosophy: Accuracy Over Performance

The core design principle of Vigilant AI is **Accuracy > Performance**. While optimization is important, the primary goal is generating **correct matches and clear, actionable reports**. This philosophy influenced every architectural decision:

- **Comprehensive evidence gathering** over fast shortcuts
- **Semantic understanding** over pattern matching
- **Multi-agent collaboration** over monolithic processing
- **Rich reporting** over minimal output

---

## Why Multi-Agent Architecture?

### Comparison with Single-Agent Approach

| Aspect | Multi-Agent (Vigilant AI) | Single-Agent Approach |
|--------|---------------------------|----------------------|
| **Separation of Concerns** | Each agent specializes in one domain (planning, vision, OCR, verification) | One monolithic prompt handling everything |
| **Prompt Complexity** | Focused, manageable prompts per agent | Massive, complex prompts prone to drift and hallucination |
| **Debugging** | Isolate issues to specific agent | Difficult to trace errors in combined logic |
| **LLM Token Usage** | Optimized per-task context | Large context windows for every call |
| **Extensibility** | Add new agents without affecting others | Changes require rewriting entire flow |
| **Accuracy** | Specialized agents achieve higher precision | Generalist approach leads to trade-offs |
| **Error Recovery** | Agents can retry independently | Single failure breaks entire pipeline |

**Why we chose Multi-Agent:**
A single agent attempting to parse planning logs, extract video frames, run OCR, perform vision analysis, AND verify test steps would require an enormous context window and complex prompt engineering. By decomposing the problem, each agent operates in its area of expertise with focused prompts, leading to **higher accuracy and better explainability**.

---

## Framework Comparison

### Why Custom Orchestration vs. AutoGen, LangChain, Haystack

| Framework | Pros | Cons | Why Not Chosen |
|-----------|------|------|----------------|
| **LangChain** | Rich ecosystem, extensive integrations, chains/agents abstraction | Heavy abstraction overhead, debugging complexity, version instability | Abstraction layers add latency and obscure control flow; video/multimodal support requires custom extensions anyway |
| **AutoGen** | Multi-agent conversations, code execution, flexible patterns | Conversation-focused (less suited for pipeline workflows), Microsoft ecosystem lock-in | Designed for interactive agent chat, not batch video analysis pipelines |
| **Haystack** | Strong document/RAG focus, production-ready pipelines | Primarily text/document oriented, limited multimodal support | Video analysis and OCR integration not first-class citizens |
| **Custom (Vigilant AI)** | Full control, minimal dependencies, optimized for video analysis | Requires more initial development | Purpose-built for the exact use case with no framework overhead |

### Detailed Framework Analysis

**LangChain**
- ✅ Would provide easy LLM provider switching
- ✅ Has image processing utilities
- ❌ Chains become complex for multi-stage video pipelines
- ❌ Debugging tool call failures is challenging
- ❌ Framework updates frequently break existing code
- **Verdict**: Overhead outweighs benefits for our specialized use case

**AutoGen**
- ✅ Excellent for multi-agent conversations
- ✅ Built-in code execution capabilities
- ❌ Designed for conversational back-and-forth, not linear pipelines
- ❌ Would require significant customization for video frame handling
- ❌ Agent termination conditions need careful tuning
- **Verdict**: Great for chat-based agents, but mismatch for structured verification workflow

**Haystack**
- ✅ Production-ready with excellent documentation
- ✅ Strong pipeline abstraction
- ❌ Text/document-centric architecture
- ❌ Video frame extraction would be external to pipeline
- ❌ OCR integration requires custom components
- **Verdict**: Would require extensive customization, losing framework benefits

**Our Custom Approach**
- ✅ **Zero framework overhead**: Direct OpenCV, EasyOCR, and LLM API calls
- ✅ **Full control**: Exact control over frame selection, batching, and caching
- ✅ **Minimal dependencies**: Only production-ready, stable libraries
- ✅ **Video-first design**: Architecture built around video analysis from the start
- ✅ **Easy debugging**: Clear agent boundaries and explicit data flow

---

## Advantages Over Alternative Approaches

| Aspect | Vigilant AI (Our Approach) | Per-Frame Analysis | Screenshot Comparison | Traditional Assertion-Only |
|--------|---------------------------|--------------------|-----------------------|---------------------------|
| **LLM API Calls** | 1-3 calls total | 100+ calls per video | 0 (no AI) | 0 |
| **Cost Efficiency** | ~90% savings | Very expensive | Free but limited | Free |
| **Semantic Understanding** | Full temporal context | Limited per-frame | None | Code-level only |
| **False Positive Detection** | Contradiction detection | Possible but expensive | Pixel-diff only | Cannot detect |
| **Temporal Ordering** | Respects step sequence | No ordering | Static snapshots | N/A |
| **Video Analysis** | Complete narrative | Fragmented | No video support | No video support |
| **Adaptability** | Smart triage saves calls | Fixed approach | Fixed comparison | Fixed assertions |

### Key Architectural Advantages

#### 1. Single-Pass Vision Analysis
The `ComprehensiveVisionAgent` analyzes ALL key frames in ONE LLM call, creating a rich `VideoTimeline` with temporal events. This approach:
- Reduces API costs by 90-99% compared to per-frame analysis
- Provides context-aware understanding (LLM sees the full story)
- Enables temporal reasoning about event sequences
- Eliminates redundant processing of similar frames

#### 2. Smart Triage System
The `VerificationAgent` intelligently decides when LLM verification is truly needed:
- Uses `NEGATIVE_INDICATORS` list to detect potential failures requiring deeper analysis
- Falls back to efficient code-based matching for obvious cases
- Batches multiple LLM requests for throughput optimization
- Adapts strategy based on test complexity and evidence quality

#### 3. Contradiction Detection
Explicitly looks for patterns that indicate test framework false positives:
- Searches for "NOT visible", "error", "failed", "exception" in OCR text
- Cross-references test pass status with visual evidence
- Catches cases where test reports success but UI shows failure
- Provides detailed reasoning for detected contradictions

#### 4. Temporal Evidence Gathering
Respects the sequential nature of test execution:
- Evidence for step N must occur AFTER evidence for step N-1
- Prevents false matches from earlier (irrelevant) frames
- Tracks timestamp progression through the test
- Enables verification of action sequences, not just individual states

#### 5. Modular LLM Provider
Factory pattern allows flexible LLM backend selection:
- **Gemini** (primary): Google's multimodal model with vision capabilities
- **CLI Wrapper**: Integration with command-line LLM tools
- **Open Source Models**: Support for self-hosted alternatives
- No code changes required to switch providers

#### 6. Robust JSON Parsing
Multiple repair strategies handle malformed LLM responses:
- Markdown fence removal (`json ...`)
- Quote character fixing (smart quotes → standard quotes)
- Partial JSON extraction from verbose responses
- Graceful degradation with default values

---

## Data Models

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATA MODELS                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────┐              ┌─────────────────────────────────────────┐
│         TestStep            │              │            TimelineEvent                │
├─────────────────────────────┤              ├─────────────────────────────────────────┤
│ + step_number: int          │              │ + timestamp: float                      │
│ + description: string       │              │ + frame_number: int                     │
│ + action: string            │              │ + event_type: string                    │
│ + expected_outcome: string  │              │ + description: string                   │
└──────────────┬──────────────┘              │ + ui_elements: list                     │
               │                             │ + text_visible: list                    │
               │ input                       │ + confidence: float                     │
               │                             └──────────────────┬──────────────────────┘
               │                                                │
               │                                                │ contains
               │                                                ▼
               │                             ┌─────────────────────────────────────────┐
               │                             │            VideoTimeline                │
               │                             ├─────────────────────────────────────────┤
               │                             │ + total_duration: float                 │
               │                             │ + total_frames_analyzed: int            │
               │                             │ + events: list                          │
               │                             │ + narrative: string                     │
               │                             │ + find_events_matching()                │
               │                             └──────────────────┬──────────────────────┘
               │                                                │
               │                                                │ provides
               │                                                ▼
               │                             ┌─────────────────────────────────────────┐
               │                             │            StepEvidence                 │
               │                             ├─────────────────────────────────────────┤
               │                             │ + found: bool                           │
               │                             │ + confidence: float                     │
               │                             │ + timestamp: float                      │
               │                             │ + matching_events: list                 │
               │                             │ + reasoning: string                     │
               │                             └──────────────────┬──────────────────────┘
               │                                                │
               │                                                │ supports
               │                                                ▼
               └────────────────────────────►┌─────────────────────────────────────────┐
                                             │         VerificationResult              │
                                             ├─────────────────────────────────────────┤
                                             │ + step: TestStep                        │
                                             │ + status: string                        │
                                             │ + confidence: float                     │
                                             │ + evidence: string                      │
                                             └──────────────────┬──────────────────────┘
                                                                │
                                                                │ aggregates
                                                                ▼
                                             ┌─────────────────────────────────────────┐
                                             │          DeviationReport                │
                                             ├─────────────────────────────────────────┤
                                             │ + test_name: string                     │
                                             │ + total_steps: int                      │
                                             │ + observed_steps: int                   │
                                             │ + deviated_steps: int                   │
                                             │ + pass_rate: float                      │
                                             │ + results: list                         │
                                             └─────────────────────────────────────────┘
```

### Model Relationships

| Model | Purpose | Key Relationships |
|-------|---------|-------------------|
| `TestStep` | Represents a single test action to verify | Input to verification, linked to result |
| `TimelineEvent` | Single moment in the video timeline | Aggregated into VideoTimeline |
| `VideoTimeline` | Complete narrative of video content | Provides evidence for all steps |
| `StepEvidence` | Gathered proof for one test step | Connects timeline to verification |
| `VerificationResult` | Final verdict for one step | Contains step, status, and evidence |
| `DeviationReport` | Aggregated results for entire test | Collection of all VerificationResults |

---

## Summary

### Key Architectural Takeaways

1. **Multi-Agent Design**: Specialized agents handle distinct responsibilities (planning, vision, OCR, verification) while the orchestrator coordinates the workflow.

2. **Efficiency First**: The single-pass vision analysis and smart triage system minimize expensive LLM calls while maintaining high verification accuracy.

3. **Temporal Awareness**: Unlike simple screenshot comparison, the system understands the sequential nature of test execution and respects step ordering.

4. **Contradiction Detection**: Goes beyond simple assertion checking to identify false positives where tests pass but the UI shows errors.

5. **Modular Infrastructure**: Factory patterns and abstract base classes enable easy extension and provider swapping without architectural changes.

6. **Multi-Format Output**: Reports are generated in formats suitable for different audiences: developers (JSON), stakeholders (HTML), and documentation (Markdown).

7. **Robust Error Handling**: Multiple fallback strategies for JSON parsing, frame extraction, and LLM failures ensure graceful degradation.

---