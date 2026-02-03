"""FastAPI backend for the analysis agent system."""

import asyncio
import logging
import warnings
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import uvicorn
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List
import uuid

from analysis_agent.core.config import get_settings
from analysis_agent.core.models import (
    TaskProgress, TaskStatus, AnalysisResult
)
from analysis_agent.agents import OrchestratorAgent
from analysis_agent.utils.parsers import PlanningLogParser, TestOutputParser
from analysis_agent.utils.report_generator import ReportGenerator

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*pin_memory.*")
warnings.filterwarnings("ignore", message=".*MPS.*")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce uvicorn access log verbosity
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

# Initialize FastAPI
app = FastAPI(
    title="Video Analysis Agent API",
    description="Multi-agent system for test verification",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
tasks: Dict[str, TaskProgress] = {}
results: Dict[str, AnalysisResult] = {}

# Initialize settings and orchestrator
settings = get_settings()
orchestrator = OrchestratorAgent(settings)


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "service": "Video Analysis Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_tasks": len([t for t in tasks.values() if t.status == TaskStatus.PROCESSING])
    }


@app.post("/analyze")
async def analyze(
    planning_log: UploadFile = File(...),
    test_output: UploadFile = File(...),
    videos: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Start video analysis.
    
    Args:
        planning_log: Agent planning log JSON file
        test_output: Test output XML file
        videos: List of video recording files (supports multiple videos)
        
    Returns:
        Task ID for tracking progress
    """
    task_id = str(uuid.uuid4())
    
    # Create task entry
    tasks[task_id] = TaskProgress(
        task_id=task_id,
        status=TaskStatus.PENDING,
        progress=0.0,
        phase="pending",
        current_step="Initializing",
        message=f"Task created with {len(videos)} video(s), waiting to start..."
    )
    
    # Read all video contents
    video_data = []
    for video in videos:
        video_data.append({
            "content": await video.read(),
            "filename": video.filename
        })
    
    # Start analysis in background
    background_tasks.add_task(
        run_analysis,
        task_id,
        await planning_log.read(),
        await test_output.read(),
        video_data,
        planning_log.filename,
        test_output.filename
    )
    
    logger.info(f"Created analysis task: {task_id} with {len(videos)} video(s)")
    
    return {
        "task_id": task_id,
        "status": "created",
        "message": f"Analysis task started with {len(videos)} video(s)"
    }


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status and progress."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    return {
        "task_id": task_id,
        "status": task.status.value,
        "progress": task.progress,
        "phase": task.phase,
        "current_step": task.current_step,
        "message": task.message,
        "timestamp": task.timestamp.isoformat(),
        "error": task.error
    }


@app.get("/tasks/{task_id}/result")
async def get_result(task_id: str):
    """Get analysis result."""
    if task_id not in results:
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = tasks[task_id]
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Task not completed yet. Status: {task.status.value}"
            )
        raise HTTPException(status_code=404, detail="Result not found")
    
    result = results[task_id]
    report = result.report
    
    return {
        "task_id": task_id,
        "report": report.model_dump(mode='json'),
        "frames_extracted": result.frames_extracted,
        "processing_time": result.processing_time,
        # V2 Metrics
        "execution_time": report.execution_time,
        "total_llm_calls": report.total_llm_calls,
        "agent_metrics": [m.model_dump(mode='json') for m in report.agent_metrics],
        "phase_metrics": report.phase_metrics
    }


@app.get("/tasks/{task_id}/download/{format}")
async def download_report(task_id: str, format: str):
    """
    Download report in specified format.
    
    Args:
        task_id: Task ID
        format: Report format (json, html, markdown)
    """
    if task_id not in results:
        raise HTTPException(status_code=404, detail="Result not found")
    
    result = results[task_id]
    
    if format == "json":
        content = result.json_report
        media_type = "application/json"
        filename = "deviation_report.json"
    elif format == "html":
        content = result.html_report
        media_type = "text/html"
        filename = "deviation_report.html"
    elif format == "markdown":
        content = result.markdown_report
        media_type = "text/markdown"
        filename = "deviation_report.md"
    else:
        raise HTTPException(status_code=400, detail="Invalid format")
    
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task and its results."""
    if task_id in tasks:
        del tasks[task_id]
    if task_id in results:
        del results[task_id]
    
    return {"message": "Task deleted"}


async def run_analysis(
    task_id: str,
    planning_log_content: bytes,
    test_output_content: bytes,
    video_data: List[Dict],
    planning_log_filename: str,
    test_output_filename: str
):
    """Run analysis in background with support for multiple videos.
    
    Args:
        task_id: Unique task identifier
        planning_log_content: Raw bytes of planning log JSON
        test_output_content: Raw bytes of test output XML
        video_data: List of dicts with 'content' (bytes) and 'filename' (str) for each video
        planning_log_filename: Original filename of planning log
        test_output_filename: Original filename of test output
    """
    start_time = datetime.now()
    
    def update_progress(progress: TaskProgress):
        """Update task progress."""
        progress.task_id = task_id
        tasks[task_id] = progress
    
    try:
        # Update status to processing
        update_progress(TaskProgress(
            task_id=task_id,
            status=TaskStatus.PROCESSING,
            progress=0.0,
            phase="parsing",
            current_step="Parsing",
            message=f"Parsing input files... ({len(video_data)} video(s))"
        ))
        
        # Create temp directory for this task
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Save all video files
            video_paths = []
            for video in video_data:
                video_path = temp_path / video["filename"]
                video_path.write_bytes(video["content"])
                video_paths.append(video_path)
            
            logger.info(f"Task {task_id}: Saved {len(video_paths)} video file(s)")
            
            # Parse inputs
            planning_log = PlanningLogParser.parse(planning_log_content)
            test_output = TestOutputParser.parse(test_output_content)
            
            logger.info(f"Task {task_id}: Parsed {len(planning_log.steps)} steps")
            
            # Run orchestrator with multiple videos
            report = await orchestrator.execute_verification(
                planning_log=planning_log,
                test_output=test_output,
                video_paths=video_paths,
                temp_dir=temp_path,
                progress_callback=update_progress
            )
            
            # Generate reports
            report_gen = ReportGenerator()
            json_report = report_gen.generate_json(report)
            html_report = report_gen.generate_html(report)
            markdown_report = report_gen.generate_markdown(report)
            
            # Count frames from all frame directories
            frames_extracted = 0
            frames_dir = temp_path / "frames"
            if frames_dir.exists():
                frames_extracted = len(list(frames_dir.glob("*.jpg")))
            
            # Store result
            processing_time = (datetime.now() - start_time).total_seconds()
            
            results[task_id] = AnalysisResult(
                task_id=task_id,
                report=report,
                json_report=json_report,
                html_report=html_report,
                markdown_report=markdown_report,
                frames_extracted=frames_extracted,
                processing_time=processing_time
            )
            
            # Mark as completed
            final_progress = TaskProgress(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                progress=1.0,
                phase="complete",
                current_step="Complete",
                message=f"Analysis completed in {processing_time:.1f}s ({len(video_paths)} video(s) processed)"
            )
            update_progress(final_progress)
            
            logger.info(f"Task {task_id}: Completed successfully with {len(video_paths)} video(s)")
    
    except Exception as e:
        logger.error(f"Task {task_id}: Failed with error: {e}", exc_info=True)
        
        # Mark as failed
        failed_progress = TaskProgress(
            task_id=task_id,
            status=TaskStatus.FAILED,
            progress=tasks[task_id].progress if task_id in tasks else 0.0,
            phase="error",
            current_step="Error",
            message=str(e),
            error=str(e)
        )
        update_progress(failed_progress)


def start_api():
    """Start the FastAPI server."""
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="warning",  # Suppress INFO logs
        access_log=False  # Disable access logs
    )


if __name__ == "__main__":
    start_api()