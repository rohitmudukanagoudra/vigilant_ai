import streamlit as st
import requests
import pandas as pd
import time
import json
import base64
from datetime import datetime
from pathlib import Path

API_URL = "http://localhost:8000"

# Get the path to the logo image
LOGO_PATH = Path(__file__).parent / "images" / "Vigilant AI logo.png"

# ------------------------------------------------------------
# Page Configuration
# ------------------------------------------------------------
st.set_page_config(
    page_title="Vigilant AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------
# Custom CSS (Exquisite Styling)
# ------------------------------------------------------------
def load_custom_css():
    """Load custom CSS for exquisite styling."""
    st.markdown("""
    <style>
    /* ============ ROOT VARIABLES ============ */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --success-gradient: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        --warning-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --danger-gradient: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        --info-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        
        --primary-color: #667eea;
        --secondary-color: #764ba2;
        --success-color: #11998e;
        --warning-color: #f5576c;
        --danger-color: #eb3349;
        
        --bg-dark: #0e1117;
        --bg-card: #1a1f2e;
        --bg-hover: #252b3b;
        --text-primary: #ffffff;
        --text-secondary: #a0aec0;
        --border-color: #2d3748;
        
        --shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.1);
        --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.15);
        --shadow-lg: 0 8px 25px rgba(0, 0, 0, 0.2);
        --shadow-glow: 0 0 20px rgba(102, 126, 234, 0.3);
    }
    
    /* ============ GLOBAL STYLES ============ */
    .stApp {
        background: linear-gradient(180deg, #0e1117 0%, #1a1f2e 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ============ SIDEBAR STYLES ============ */
    section[data-testid="stSidebar"] {
        background-color: var(--bg-card) !important;
        border-right: 1px solid var(--border-color);
    }
    
    section[data-testid="stSidebar"] .block-container {
        padding-top: 3rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }
    
    /* ============ HEADER STYLES ============ */
    .main-header {
        background: var(--primary-gradient);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: var(--shadow-lg), var(--shadow-glow);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: shimmer 10s infinite linear;
    }
    
    @keyframes shimmer {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        position: relative;
        z-index: 1;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
        position: relative;
        z-index: 1;
    }
    
    /* ============ UPLOAD SECTION ============ */
    .upload-section {
        background: var(--bg-card);
        border: 2px dashed var(--border-color);
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }
    
    .upload-section:hover {
        border-color: var(--primary-color);
        box-shadow: var(--shadow-glow);
    }
    
    /* ============ METRIC CARDS ============ */
    .metric-card {
        background: var(--bg-card);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: var(--shadow-md);
        transition: all 0.3s ease;
        border: 1px solid var(--border-color);
        height: 100%;
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-lg);
    }
    
    .metric-card.passed { border-top: 4px solid #38ef7d; }
    .metric-card.failed { border-top: 4px solid #f45c43; }
    .metric-card.uncertain { border-top: 4px solid #ffd93d; }
    .metric-card.total { border-top: 4px solid var(--primary-color); }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .metric-value.passed { background: var(--success-gradient); -webkit-background-clip: text; background-clip: text; }
    .metric-value.failed { background: var(--danger-gradient); -webkit-background-clip: text; background-clip: text; }
    .metric-value.uncertain { background: var(--warning-gradient); -webkit-background-clip: text; background-clip: text; }
    
    .metric-label {
        color: var(--text-secondary);
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.5rem;
    }
    
    /* ============ PROGRESS SECTION ============ */
    .progress-section {
        background: var(--bg-card);
        border-radius: 16px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: var(--shadow-md);
        border: 1px solid var(--border-color);
    }
    
    .phase-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 1rem;
    }
    
    .phase-badge.planning { background: rgba(102, 126, 234, 0.2); color: #667eea; }
    .phase-badge.extraction { background: rgba(79, 172, 254, 0.2); color: #4facfe; }
    .phase-badge.ocr { background: rgba(240, 147, 251, 0.2); color: #f093fb; }
    .phase-badge.vision { background: rgba(17, 153, 142, 0.2); color: #11998e; }
    .phase-badge.verification { background: rgba(245, 87, 108, 0.2); color: #f5576c; }
    .phase-badge.complete { background: rgba(56, 239, 125, 0.2); color: #38ef7d; }
    .phase-badge.error { background: rgba(235, 51, 73, 0.2); color: #eb3349; }
    
    /* Custom Progress Bar Override */
    div[data-testid="stProgress"] > div > div > div > div {
        background: var(--primary-gradient);
        box-shadow: 0 0 10px rgba(102, 126, 234, 0.5);
    }
    
    /* ============ TABS STYLES ============ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background-color: transparent;
        border-bottom: 2px solid var(--border-color);
        padding-bottom: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: var(--bg-hover);
        border-radius: 8px;
        color: var(--text-secondary);
        font-weight: 600;
        padding: 0 1.5rem;
        transition: all 0.3s ease;
        border: 1px solid transparent;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: var(--bg-hover);
        border-color: var(--primary-color);
        color: var(--text-primary);
        transform: translateY(-2px);
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--primary-gradient) !important;
        color: white !important;
        border: none !important;
        box-shadow: var(--shadow-glow);
    }

    /* ============ BUTTONS ============ */
    .stButton > button {
        background: var(--primary-gradient) !important;
        color: white !important;
        border: none !important;
        padding: 0.75rem 2rem !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        box-shadow: var(--shadow-md) !important;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-lg), var(--shadow-glow) !important;
    }
    
    /* ============ ALERTS ============ */
    div[data-testid="stToast"] {
        background: var(--bg-card);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

load_custom_css()

# ------------------------------------------------------------
# Session State & Helper Functions
# ------------------------------------------------------------
if "task_id" not in st.session_state:
    st.session_state.task_id = None
if "status" not in st.session_state:
    st.session_state.status = "idle" # idle, processing, completed, failed
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None
if "progress_cache" not in st.session_state:
    st.session_state.progress_cache = {"progress": 0.0, "step": "Initializing", "phase": "starting"}
if "error_retry_count" not in st.session_state:
    st.session_state.error_retry_count = 0

def start_analysis_task(files):
    """Sends files to the backend to start a new analysis task.
    
    Args:
        files: List of tuples (field_name, (filename, data, content_type))
               Supports multiple files with the same field name (e.g., multiple videos)
    """
    try:
        with st.spinner("🚀 Uploading artifacts and initializing agents..."):
            resp = requests.post(f"{API_URL}/analyze", files=files, timeout=120)
            resp.raise_for_status()
        
        st.session_state.task_id = resp.json()["task_id"]
        st.session_state.status = "processing"
        st.session_state.analysis_data = None
        st.session_state.progress_cache = {"progress": 0.0, "step": "Initializing", "phase": "starting"}
        st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to start analysis: {str(e)}")

# ------------------------------------------------------------
# Sidebar - Input Zone
# ------------------------------------------------------------
with st.sidebar:
    # Logo/Brand Section
    if LOGO_PATH.exists():
        # Center the logo with reduced size
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(str(LOGO_PATH), width="stretch")
    
    # Always show the name below the logo
    st.markdown("""
    <div style="text-align: center; margin-top: -1rem; padding-bottom: 0.5rem;">
        <h3 style="margin: 0; color: white; font-size: 1.3rem;">Vigilant AI</h3>
        <p style="color: #a0aec0; font-size: 0.8rem; margin: 0.25rem 0 0 0;">AI-Powered Test Verification</p>
    </div>
    """, unsafe_allow_html=True)
    
    # API Status
    try:
        api_online = requests.get(f"{API_URL}/health", timeout=3).status_code == 200
    except:
        api_online = False
    
    status_color = "#38ef7d" if api_online else "#f45c43"
    status_text = "Online" if api_online else "Offline"
    
    st.markdown(f"""
    <div style="background: #0e1117; padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem; border: 1px solid #2d3748;">
        <div style="font-size: 0.9rem; font-weight: 600; color: white; margin-bottom: 0.5rem;">🔌 API Status</div>
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <div style="width: 8px; height: 8px; background: {status_color}; border-radius: 50%;"></div>
            <span style="color: {status_color}; font-size: 0.85rem;">{status_text}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Store uploaded files in session state to persist them
    if "uploaded_planning_log" not in st.session_state:
        st.session_state.uploaded_planning_log = None
    if "uploaded_test_output" not in st.session_state:
        st.session_state.uploaded_test_output = None
    if "uploaded_videos" not in st.session_state:
        st.session_state.uploaded_videos = []
    
    # Check if we're in a state where uploads should be hidden (processing or completed)
    hide_uploads = st.session_state.status in ["processing", "completed"]
    
    # File Upload Section - only show if idle (before clicking Start Analysis)
    if st.session_state.status == "idle":
        st.markdown("**📋 Planning Log** (JSON)")
        planning_log = st.file_uploader("Upload Planning Log", type=["json"], label_visibility="collapsed")
        if planning_log:
            st.session_state.uploaded_planning_log = {"name": planning_log.name, "data": planning_log.getvalue()}
        
        st.markdown("**📊 Test Output** (XML)")
        test_output = st.file_uploader("Upload Test Output", type=["xml"], label_visibility="collapsed")
        if test_output:
            st.session_state.uploaded_test_output = {"name": test_output.name, "data": test_output.getvalue()}
        
        st.markdown("**🎥 Session Recordings** (MP4/MOV) - Multiple Allowed")
        videos = st.file_uploader("Upload Videos", type=["mp4", "mov", "webm"], label_visibility="collapsed", accept_multiple_files=True)
        if videos:
            st.session_state.uploaded_videos = [{"name": v.name, "data": v.getvalue(), "type": v.type} for v in videos]
    
    # Show uploaded files info ONLY after clicking Start Analysis (processing or completed)
    if st.session_state.status in ["processing", "completed"]:
        has_files = (st.session_state.uploaded_planning_log is not None or
                     st.session_state.uploaded_test_output is not None or
                     len(st.session_state.uploaded_videos) > 0)
        
        if has_files:
            st.markdown("""
            <div style="background: #0e1117; padding: 0.75rem 1rem; border-radius: 8px; margin: 1rem 0; border: 1px solid #2d3748;">
                <div style="font-size: 0.9rem; font-weight: 600; color: white; margin-bottom: 0.5rem;">📁 Uploaded Files</div>
            """, unsafe_allow_html=True)
            
            files_html = ""
            if st.session_state.uploaded_planning_log:
                files_html += f'<div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.5rem; background: rgba(102, 126, 234, 0.1); border-radius: 6px; margin-bottom: 0.4rem; font-size: 0.8rem;"><span>📋</span><span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #a0aec0;">{st.session_state.uploaded_planning_log["name"]}</span><span style="color: #38ef7d;">✓</span></div>'
            for video in st.session_state.uploaded_videos:
                files_html += f'<div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.5rem; background: rgba(102, 126, 234, 0.1); border-radius: 6px; margin-bottom: 0.4rem; font-size: 0.8rem;"><span>🎥</span><span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #a0aec0;">{video["name"]}</span><span style="color: #38ef7d;">✓</span></div>'
            
            st.markdown(files_html + "</div>", unsafe_allow_html=True)

    # Footer section with buttons
    st.markdown("---")
    
    # Check if all files are uploaded
    all_files = (st.session_state.uploaded_planning_log is not None and
                 st.session_state.uploaded_test_output is not None and
                 len(st.session_state.uploaded_videos) > 0)
    
    # Start Analysis Button - show at footer when idle and all files uploaded
    if all_files and st.session_state.status == "idle":
        if st.button("🚀 START ANALYSIS", key="sidebar_start"):
            # Build files list with multiple videos
            files = [
                ("planning_log", (st.session_state.uploaded_planning_log["name"],
                               st.session_state.uploaded_planning_log["data"],
                               "application/json")),
                ("test_output", (st.session_state.uploaded_test_output["name"],
                              st.session_state.uploaded_test_output["data"],
                              "application/xml")),
            ]
            # Add all videos with the same field name for multipart handling
            for video in st.session_state.uploaded_videos:
                files.append(("videos", (video["name"], video["data"], video["type"])))
            
            start_analysis_task(files)
    
    # Start New Analysis button - show at footer when completed
    if st.session_state.status == "completed":
        if st.button("🔄 Start New Analysis", key="sidebar_new"):
            st.session_state.status = "idle"
            st.session_state.task_id = None
            st.session_state.analysis_data = None
            # Clear uploaded files
            st.session_state.uploaded_planning_log = None
            st.session_state.uploaded_test_output = None
            st.session_state.uploaded_videos = []
            st.rerun()


# ------------------------------------------------------------
# Main Content Area
# ------------------------------------------------------------

# HEADER
st.markdown("""
<div class="main-header">
    <h1>Vigilant AI</h1>
    <p>AI-Powered Test Verification System</p>
</div>
""", unsafe_allow_html=True)

# STATES
if st.session_state.status == "processing":
    st.markdown('<div class="progress-section">', unsafe_allow_html=True)
    st.subheader("⚡ Analysis Active")
    
    # Progress UI
    current_cache = st.session_state.progress_cache
    st.markdown(f"**Phase: {current_cache['phase'].upper()}**")
    st.markdown(f"*{current_cache['step']}*")
    st.progress(current_cache["progress"])
    
    # Intelligent Polling
    try:
        response = requests.get(f"{API_URL}/tasks/{st.session_state.task_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            st.session_state.error_retry_count = 0 # Reset error count on success
            
            # Update cache if changed
            if data["progress"] != current_cache["progress"] or data["current_step"] != current_cache["step"]:
                st.session_state.progress_cache = {
                    "progress": data["progress"],
                    "step": data["current_step"],
                    "phase": data["phase"]
                }
                st.rerun() # Refresh immediately on change
            
            # Check completion
            if data["status"] in ["completed", "failed"]:
                st.session_state.status = data["status"]
                st.rerun()
            else:
                time.sleep(1) # Wait before next poll
                st.rerun()
        else:
            raise Exception(f"Server returned {response.status_code}")
            
    except Exception as e:
        # Graceful degradation - don't show error unless it persists
        st.session_state.error_retry_count += 1
        if st.session_state.error_retry_count > 5:
            st.warning(f"Connection unstable... Retrying ({st.session_state.error_retry_count})")
        
        time.sleep(2)
        st.rerun()
        
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.status == "completed":
    if not st.session_state.analysis_data:
        with st.spinner("Generating final report..."):
            resp = requests.get(f"{API_URL}/tasks/{st.session_state.task_id}/result")
            st.session_state.analysis_data = resp.json()
    
    data = st.session_state.analysis_data
    report = data["report"]
    
    # SUMMARY METRICS ROW
    m1, m2, m3, m4 = st.columns(4)
    status_cls = "passed" if report["overall_status"] == "PASSED" else "failed" if report["overall_status"] == "FAILED" else "uncertain"
    
    m1.markdown(f'<div class="metric-card {status_cls}"><div class="metric-value {status_cls}">{report["overall_status"]}</div><div class="metric-label">Overall Status</div></div>', unsafe_allow_html=True)
    m1.markdown("") # Spacer
    m2.markdown(f'<div class="metric-card"><div class="metric-value">{report["pass_rate"]:.1f}%</div><div class="metric-label">Pass Rate</div></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="metric-card"><div class="metric-value">{report["observed_steps"]}/{report["total_steps"]}</div><div class="metric-label">Observed Steps</div></div>', unsafe_allow_html=True)
    # Correct key for processing time might be needed if not in root of response
    duration_val = data.get("processing_time", 0)
    m4.markdown(f'<div class="metric-card"><div class="metric-value">{duration_val:.0f}s</div><div class="metric-label">Duration</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # TABS FOR DETAILS
    tab1, tab2, tab3 = st.tabs(["📊 Summary Details", "🔎 Stepwise Analysis", "🤖 Agent Insights"])
    
    with tab1:
        st.markdown("### 📋 Executive Summary")
        # Summary Table with proper status colors
        summary_data = []
        for res in report["verification_results"]:
            status = res["status"]
            status_lower = status.lower()
            if status_lower in ["passed", "observed"]:
                emoji = "✅"
            elif status_lower in ["failed", "deviation"]:
                emoji = "❌"
            else:
                emoji = "⚠️"
            summary_data.append({
                "Step": f"Step {res['step']['step_number']}",
                "Status": f"{emoji} {status}",
                "Confidence": f"{res['confidence']*100:.1f}%",
                "Description": res["step"]["description"]
            })
        st.dataframe(pd.DataFrame(summary_data), width='stretch' , hide_index=True)

    with tab2:
        st.markdown("### 🔬 Detailed Step Verification")
        results = report["verification_results"]
        for res in results:
            status = res["status"]
            # Use caution emoji only for issues, green check for passed/observed
            status_lower = status.lower()
            if status_lower in ["passed", "observed"]:
                icon = "✅"
                color = "#38ef7d"  # Green
            elif status_lower in ["failed", "deviation"]:
                icon = "⚠️"  # Caution for issues
                color = "#f45c43"  # Red
            else:
                icon = "⚠️"
                color = "#ffd93d"  # Yellow
            
            with st.expander(f"{icon} Step {res['step']['step_number']}: {res['step']['description']}"):
                c1, c2 = st.columns([3, 1])
                with c1:
                    # Display evidence with appropriate styling based on status
                    if status_lower in ["passed", "observed"]:
                        st.success(f"**Evidence:** {res['evidence']}")
                    elif status_lower in ["failed", "deviation"]:
                        st.error(f"**Evidence:** {res['evidence']}")
                    else:
                        st.warning(f"**Evidence:** {res['evidence']}")
                    
                    if res.get("explanation"):
                        st.info(f"💡 {res['explanation']}")
                    if res.get("reasoning"):
                        st.markdown(f"**Detailed Reasoning:**\n{res['reasoning']}")
                    
                    # Show matching events if available
                    if res.get("matching_events"):
                        st.markdown("**Matching Timeline Events:**")
                        for evt in res["matching_events"]:
                            st.code(f"[{evt['timestamp']:.1f}s] {evt['description']}")
                            
                with c2:
                    st.markdown(f"<h3 style='color:{color}; margin-top:0'>{status}</h3>", unsafe_allow_html=True)
                    st.caption(f"Confidence: {res['confidence']:.2f}")
                    if res.get("video_timestamp"):
                        st.caption(f"Timestamp: {res['video_timestamp']:.2f}s")
                    if res.get("frame_number"):
                        st.caption(f"Frame: {res['frame_number']}")

    with tab3:
        st.markdown("### 🤖 Agent Performance Metrics")
        
        # Mock metrics for now - ideally these come from the backend response
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total LLM Calls", "2", delta="-90% vs Legacy")
        with c2:
            st.metric("Vision Analysis Time", f"{duration_val/2:.1f}s", delta="Single Pass")
            
        st.markdown("#### 🧠 Verification Strategy Used")
        # Display strategy if available in data
        # st.json(data.get("strategy", {}))
        st.info("Strategy: Hybrid Vision + OCR Analysis with Single-Pass Video Understanding")
    
    # Export Reports button - positioned at right side after tabs
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 2, 1])
    with col3:
        # Generate reports for export
        json_report = json.dumps(data, indent=2)
        
        # Markdown report
        md_report = f"""# Vigilant AI Analysis Report
**Task ID:** {data.get('task_id')}
**Status:** {report.get('overall_status')}
**Pass Rate:** {report.get('pass_rate')}%

## Executive Summary
{report.get('summary')}

## Verification Details
"""
        for res in report.get('verification_results', []):
            step = res.get('step', {})
            status = res.get('status', 'UNKNOWN')
            status_lower = status.lower()
            if status_lower in ["passed", "observed"]:
                emoji = "✅"
            else:
                emoji = "⚠️"
            md_report += f"""
### {emoji} Step {step.get('step_number')}: {status.upper()}
**Description:** {step.get('description', 'No description')}
**Confidence:** {res.get('confidence', 0.0):.2f}
**Evidence:** {res.get('evidence', 'No evidence provided')}
"""

        # HTML report
        overall_status = report.get('overall_status', 'UNKNOWN')
        overall_lower = overall_status.lower()
        if overall_lower == "passed":
            overall_color = "#38ef7d"
        elif overall_lower == "failed":
            overall_color = "#f45c43"
        else:
            overall_color = "#ffd93d"
        
        html_report = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vigilant AI Report {data.get('task_id')}</title>
    <style>
        :root {{
            --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --observed-color: #38ef7d;
            --uncertain-color: #ffd93d;
            --deviation-color: #f45c43;
            --bg-dark: #0e1117;
            --bg-card: #1a1f2e;
            --text-primary: #ffffff;
            --text-secondary: #a0aec0;
            --border-color: #2d3748;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background: linear-gradient(180deg, #0e1117 0%, #1a1f2e 100%);
            min-height: 100vh;
            padding: 2rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: var(--primary-gradient);
            padding: 2.5rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
            display: flex;
            align-items: center;
            gap: 2rem;
        }}
        .header-logo {{ flex-shrink: 0; }}
        .header-logo img {{ max-width: 100px; height: auto; }}
        .header-content {{ flex: 1; }}
        .header h1 {{ color: white; font-size: 2.5rem; font-weight: 700; margin: 0 0 0.5rem 0; }}
        .header .meta {{ color: rgba(255,255,255,0.8); font-size: 0.9rem; }}
        .status-banner {{
            background: {overall_color};
            padding: 1.5rem 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
        }}
        .status-banner h2 {{ color: white; font-size: 1.8rem; margin: 0; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .metric-card {{
            background: var(--bg-card);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            border: 1px solid var(--border-color);
        }}
        .metric-value {{ font-size: 2.5rem; font-weight: 700; color: #667eea; }}
        .metric-label {{ color: var(--text-secondary); font-size: 0.9rem; text-transform: uppercase; }}
        .step-card {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border: 1px solid var(--border-color);
        }}
        .step-card.observed, .step-card.passed {{ border-left: 4px solid var(--observed-color); }}
        .step-card.deviation, .step-card.failed {{ border-left: 4px solid var(--deviation-color); }}
        .step-card.uncertain {{ border-left: 4px solid var(--uncertain-color); }}
        .step-card h3 {{ color: var(--text-primary); margin-bottom: 1rem; }}
        .step-card p {{ color: var(--text-secondary); margin-bottom: 0.5rem; }}
        .footer {{ text-align: center; padding: 2rem; color: var(--text-secondary); font-size: 0.85rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
"""
        
        # Add logo to HTML report if it exists (logo on left, text on right)
        if LOGO_PATH.exists():
            with open(LOGO_PATH, "rb") as logo_file:
                logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")
            html_report += f"""
            <div class="header-logo">
                <img src="data:image/png;base64,{logo_base64}" alt="Vigilant AI Logo">
            </div>
            <div class="header-content">
                <h1>Vigilant AI Analysis Report</h1>
                <div class="meta">Task ID: {data.get('task_id')}</div>
            </div>
        </div>
"""
        else:
            html_report += f"""
            <div class="header-content">
                <h1>Vigilant AI Analysis Report</h1>
                <div class="meta">Task ID: {data.get('task_id')}</div>
            </div>
        </div>
"""
        
        html_report += f"""
        <div class="status-banner">
            <h2>{overall_status}</h2>
        </div>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{report.get('total_steps', 0)}</div>
                <div class="metric-label">Total Steps</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" style="color: var(--observed-color);">{report.get('observed_steps', 0)}</div>
                <div class="metric-label">✅ Observed (Green)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" style="color: var(--deviation-color);">{report.get('deviated_steps', 0)}</div>
                <div class="metric-label">❌ Deviated (Red)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{report.get('pass_rate', 0):.1f}%</div>
                <div class="metric-label">Pass Rate</div>
            </div>
        </div>
        <h2 style="color: var(--text-primary); margin-bottom: 1rem;">Verification Details</h2>
"""
        for res in report.get('verification_results', []):
            status = res.get('status', 'unknown').lower()
            step = res.get('step', {})
            if status in ["passed", "observed"]:
                emoji = "✅"
            else:
                emoji = "⚠️"
            html_report += f"""
        <div class="step-card {status}">
            <h3>{emoji} Step {step.get('step_number')}: {res.get('status', 'UNKNOWN').upper()}</h3>
            <p><strong>Description:</strong> {step.get('description', 'No description')}</p>
            <p><strong>Evidence:</strong> {res.get('evidence', 'No evidence')}</p>
            <p><strong>Confidence:</strong> {res.get('confidence', 0.0):.1%}</p>
        </div>
"""
        html_report += """
        <div class="footer">
            <p>Generated by <strong>Vigilant AI</strong> | Built by <strong>Rohit</strong></p>
        </div>
    </div>
</body>
</html>"""
        
        with st.popover("📥 Export Reports"):
            st.download_button(
                label="📋 JSON",
                data=json_report,
                file_name=f"testzeus_report_{st.session_state.task_id}.json",
                mime="application/json",
                width='stretch',
                key="json_dl"
            )
            st.download_button(
                label="📝 Markdown",
                data=md_report,
                file_name=f"testzeus_report_{st.session_state.task_id}.md",
                mime="text/markdown",
                width='stretch',
                key="md_dl"
            )
            st.download_button(
                label="🌐 HTML",
                data=html_report,
                file_name=f"testzeus_report_{st.session_state.task_id}.html",
                mime="text/html",
                width='stretch',
                key="html_dl"
            )

elif st.session_state.status == "failed":
    st.error("Analysis Failed")
    if st.button("Retry"):
        st.session_state.status = "idle"
        st.rerun()

else:
    # IDLE STATE
    st.markdown("""
    <div style="text-align: center; padding: 4rem; opacity: 0.7;">
        <h2>Ready for Analysis</h2>
        <p>Please upload your test artifacts in the sidebar to begin.</p>
    </div>
    """, unsafe_allow_html=True)

# Main area footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 1rem 0; opacity: 0.7;">
    <p style="color: #667eea; font-size: 0.9rem; margin: 0;">
        <strong>Vigilant AI</strong> | Built by <strong>Rohit</strong>
    </p>
</div>
""", unsafe_allow_html=True)
