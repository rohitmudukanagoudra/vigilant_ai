<p align="center">
  <img src="analysis_agent/ui/images/Vigilant AI logo.png" alt="Vigilant AI Logo" width="200"/>
</p>

<h1 align="center">Vigilant AI</h1>

<p align="center">
  <strong>AI-Powered Test Verification System</strong><br>
</p>

<p align="center">
  <a href="#key-features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#configuration">Configuration</a>
</p>

---

## 🎯 Overview

**Vigilant AI** is an AI-powered test verification system that automatically verifies whether automated UI tests executed correctly by analyzing video recordings of test sessions.

### The Problem We Solve

> **"Did my automated test actually do what it was supposed to do?"**

Traditional test frameworks report pass/fail based on assertions, but they can't verify that the actual UI behavior matched expectations. Vigilant AI provides a **second layer of verification** by:

- 📋 Taking a test planning log (expected steps)
- ✅ Taking the test output (pass/fail from test framework)
- 🎬 Taking a video recording of the test execution
- 🤖 Using AI vision to verify each step was actually performed

This catches **false positives** where tests pass but the actual UI behavior deviated from expectations.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🎥 **Single-Pass Vision Analysis** | One comprehensive LLM call analyzes the entire video instead of per-frame calls. Reduces API costs by ~90%. |
| 📹 **Multiple Video Support** | Upload and analyze multiple video recordings in a single session. Frames are extracted sequentially with continuous timestamps. |
| 🧠 **Smart Triage** | Intelligent decision on when LLM verification is needed vs code-based matching. |
| 🔌 **Modular LLM Provider** | Factory pattern allows swapping between Gemini, CLI, or open-source models. |
| 📊 **Multi-format Reports** | Generate reports in JSON, HTML (styled), and Markdown formats. |

---

## 📦 Installation

### Prerequisites

- Python 3.9+
- pip or poetry

### Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd analysis_agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   LLM_PROVIDER=gemini  # Options: gemini, cli, opensource
   ```

---

## 🚀 Quick Start

### Option 1: Web UI (Streamlit)

Launch the interactive web interface:

```bash
streamlit run ui/main_ui.py
```

The UI will be available at `http://localhost:8501`

### Option 2: REST API (FastAPI)

Start the API server:

```bash
uvicorn api.main:app --reload
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### Basic Usage

1. Upload your test video recording(s) - **multiple videos are supported**
2. Provide the test planning log (expected steps)
3. Optionally include test framework output
4. Run verification
5. Review the detailed report

### Multiple Video Support

Vigilant AI supports analyzing multiple video recordings in a single session. This is useful when:
- Your test execution is split across multiple recordings
- You have different camera angles or viewpoints
- Your test session was recorded in segments

Simply select multiple video files when uploading, and the system will:
- Extract frames from each video sequentially
- Apply continuous timestamps across all videos
- Analyze all frames as a unified timeline

---

## 📁 Folder Structure

```
analysis_agent/
├── __init__.py              # Package init - defines version "1.0.0"
├── .env.example             # Environment configuration template
├── README.md                # This file
│
├── agents/                  # Multi-agent system core
│   ├── __init__.py          # Exports all agents
│   ├── base_agent.py        # Base class with LLM, logging, metrics
│   ├── orchestrator.py      # Master coordinator
│   ├── planning_agent.py    # Strategy creation agent
│   ├── comprehensive_vision_agent.py  # Single-pass video analyzer
│   ├── ocr_agent.py         # Text extraction agent
│   └── verification_agent.py # LLM-based semantic verifier
│
├── api/                     # REST API layer
│   └── main.py              # FastAPI backend
│
├── core/                    # Core infrastructure
│   ├── __init__.py          # Exports Settings, models
│   ├── config.py            # Pydantic Settings configuration
│   ├── llm_provider.py      # LLM abstraction layer (Gemini, CLI, OpenSource)
│   └── models.py            # Pydantic data models
│
├── ui/                      # Web interface
│   ├── __init__.py          # Empty
│   ├── main_ui.py           # Streamlit UI
│   └── images/
│       └── Vigilant AI logo.png
│
└── utils/                   # Utility modules
    ├── __init__.py          # Exports parsers and generators
    ├── parsers.py           # JSON/XML input parsers
    └── report_generator.py  # Multi-format report generation
```

---

## 🤖 Agent Architecture

Vigilant AI uses a multi-agent system where each agent has a specialized role:

| Agent | Role | Key Method | LLM Calls |
|-------|------|------------|-----------|
| **OrchestratorAgent** | Coordinates entire workflow, manages phases | `execute_verification()` | 0 (coordinates) |
| **PlanningAgent** | Analyzes test complexity, creates adaptive strategy | `create_strategy()` | 1 per analysis |
| **ComprehensiveVisionAgent** | Single-pass video analysis, creates timeline | `analyze_video_comprehensive()` | 1 (key innovation) |
| **OCRAgent** | Extracts text from frames using EasyOCR | `analyze_frames()` | 0 (uses EasyOCR) |
| **VerificationAgent** | Semantic step verification, contradiction detection | `verify_step_with_timeline_evidence()` | 1-N (smart triage) |

### Agent Descriptions

#### 🎭 OrchestratorAgent
The master coordinator that manages the entire verification workflow. It orchestrates the other agents, manages execution phases, and aggregates results. Does not make LLM calls directly.

#### 📋 PlanningAgent
Analyzes test complexity and creates an adaptive verification strategy. Determines the optimal approach based on the number of steps, video length, and test type.

#### 👁️ ComprehensiveVisionAgent
The key innovation of the system. Performs a single-pass analysis of the entire video, creating a comprehensive timeline of UI events. This reduces API costs by approximately 90% compared to per-frame analysis.

#### 📝 OCRAgent
Extracts text content from video frames using EasyOCR. Provides textual evidence for verification without requiring LLM calls.

#### ✅ VerificationAgent
Performs semantic verification of each test step against the evidence gathered. Uses smart triage to determine when LLM verification is needed versus simple pattern matching.

---

## 🛠️ Technologies

| Technology | Purpose |
|------------|---------|
| **FastAPI** | REST API backend with automatic OpenAPI documentation |
| **Streamlit** | Interactive web UI for easy test verification |
| **Pydantic** | Data validation, serialization, and settings management |
| **Google Gemini** | Primary LLM provider for vision and text analysis |
| **OpenCV (cv2)** | Video processing and frame extraction |
| **EasyOCR** | Text extraction from video frames |
| **PIL/Pillow** | Image processing and preparation for LLM input |

---

## ⚙️ Configuration

### Environment Variables

Configure the system by editing your `.env` file:

```env
# LLM Provider Configuration
LLM_PROVIDER=gemini              # Options: gemini, cli, opensource
GEMINI_API_KEY=your_key_here     # Required for Gemini provider

# Video Processing
FRAME_SAMPLE_RATE=1              # Frames per second to analyze
MAX_FRAMES=50                    # Maximum frames to process

# Logging
LOG_LEVEL=INFO                   # Options: DEBUG, INFO, WARNING, ERROR

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### LLM Provider Options

| Provider | Description | Configuration |
|----------|-------------|---------------|
| `gemini` | Google Gemini API (recommended) | Requires `GEMINI_API_KEY` |
| `cli` | Command-line interface for testing | No API key needed |
| `opensource` | Open-source model support | Model-specific configuration |

---

## 📄 License

This project is licensed under the terms specified in the [LICENSE](../LICENSE) file in the parent directory.

---

<p align="center">
  <strong>Vigilant AI</strong> - Trust, but verify your automated tests.
</p>