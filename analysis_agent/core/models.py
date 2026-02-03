"""Data models for the analysis agent system."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class StepStatus(str, Enum):
    """Status of a verification step."""
    OBSERVED = "observed"
    DEVIATION = "deviation"
    UNCERTAIN = "uncertain"


class TaskStatus(str, Enum):
    """Status of an analysis task."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TestStep(BaseModel):
    """A single test step from the planning log."""
    step_number: int
    description: str
    action: str
    expected_outcome: Optional[str] = None


class VideoFrame(BaseModel):
    """Information about a video frame."""
    frame_number: int
    timestamp: float
    frame_path: Optional[str] = None
    ocr_text: List[str] = Field(default_factory=list)
    vision_description: Optional[str] = None


class AgentMetrics(BaseModel):
    """Metrics for an agent's performance."""
    agent_name: str
    time_taken: float  # seconds
    llm_calls: int
    tokens_used: Optional[int] = None
    phase: str
    
class AgentDecision(BaseModel):
    """Decision made by an agent."""
    agent_name: str
    decision: str
    reasoning: str
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    metrics: Optional[AgentMetrics] = None


class VerificationResult(BaseModel):
    """Result of verifying a single test step."""
    step: TestStep
    status: StepStatus
    confidence: float
    video_timestamp: Optional[float] = None
    evidence: str
    ocr_detected_text: List[str] = Field(default_factory=list)
    vision_analysis: Optional[str] = None
    agent_decisions: List[AgentDecision] = Field(default_factory=list)
    notes: Optional[str] = None


class VerificationStrategy(BaseModel):
    """Strategy determined by the planning agent."""
    frame_interval: int
    max_frames: int
    use_batch_processing: bool
    confidence_threshold: float
    priority_mode: str  # "vision", "ocr", or "hybrid"
    reasoning: str


class DeviationReport(BaseModel):
    """Final deviation report."""
    test_name: str
    execution_date: datetime
    total_steps: int
    observed_steps: int
    deviated_steps: int
    uncertain_steps: int
    pass_rate: float = 0.0
    verification_results: List[VerificationResult]
    strategy_used: Optional[VerificationStrategy] = None
    summary: str
    overall_status: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # V2: Execution metrics
    agent_metrics: List[AgentMetrics] = Field(default_factory=list)
    execution_time: float = 0.0
    total_llm_calls: int = 0
    phase_metrics: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.total_steps > 0:
            self.pass_rate = (self.observed_steps / self.total_steps) * 100


class PlanningLog(BaseModel):
    """Parsed planning log data."""
    steps: List[TestStep]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TestOutput(BaseModel):
    """Parsed test output data."""
    test_name: str
    status: str
    duration: Optional[float] = None
    failure_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskProgress(BaseModel):
    """Progress information for a task."""
    task_id: str
    status: TaskStatus
    progress: float  # 0.0 to 1.0
    phase: str  # Machine-readable phase identifier
    current_step: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None


class AnalysisRequest(BaseModel):
    """Request to analyze files."""
    planning_log_content: bytes
    test_output_content: bytes
    video_content: bytes
    planning_log_filename: str
    test_output_filename: str
    video_filename: str


class AnalysisResult(BaseModel):
    """Result of an analysis."""
    task_id: str
    report: DeviationReport
    json_report: str
    html_report: str
    markdown_report: str
    frames_extracted: int
    processing_time: float


# V3: Comprehensive Vision Models
class TimelineEvent(BaseModel):
    """A single event in the video timeline."""
    timestamp: float
    frame_number: int
    event_type: str  # "navigation", "click", "type", "ui_change", "assertion"
    description: str
    ui_elements: List[str] = Field(default_factory=list)
    text_visible: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    screenshot_path: Optional[str] = None


class VideoTimeline(BaseModel):
    """Comprehensive timeline of video events from single-pass analysis."""
    total_duration: float
    total_frames_analyzed: int
    events: List[TimelineEvent] = Field(default_factory=list)
    narrative: str  # Overall description of what happened
    key_observations: List[str] = Field(default_factory=list)
    
    def find_events_near(self, timestamp: float, window: float = 10.0) -> List[TimelineEvent]:
        """Find events within time window."""
        return [
            e for e in self.events
            if abs(e.timestamp - timestamp) <= window
        ]
    
    def find_events_matching(
        self,
        keywords: List[str],
        min_timestamp: float = 0.0,
        require_multiple_matches: bool = True
    ) -> List[TimelineEvent]:
        """
        Find events matching keywords with scoring.
        
        Args:
            keywords: Keywords to match against
            min_timestamp: Minimum timestamp (for temporal ordering)
            require_multiple_matches: If True, require at least 2 keyword matches
            
        Returns:
            List of matching events sorted by relevance score
        """
        scored_matches = []
        
        for event in self.events:
            # Skip events before minimum timestamp (temporal ordering)
            if event.timestamp < min_timestamp:
                continue
                
            desc_lower = event.description.lower()
            text_lower = ' '.join(event.text_visible).lower()
            ui_lower = ' '.join(event.ui_elements).lower()
            combined = f"{desc_lower} {text_lower} {ui_lower}"
            
            # Count keyword matches
            matches = 0
            matched_keywords = []
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in combined:
                    matches += 1
                    matched_keywords.append(kw)
            
            # Apply minimum match requirement
            if require_multiple_matches and matches < 2:
                continue
            elif not require_multiple_matches and matches < 1:
                continue
            
            # Calculate relevance score
            score = matches / max(len(keywords), 1)
            
            # Boost for exact phrase matches in description
            for kw in keywords:
                if len(kw) > 3 and kw.lower() in desc_lower:
                    score += 0.2
            
            # Boost based on event type relevance
            event_type_boosts = {
                "click": 0.1,
                "type": 0.1,
                "ui_change": 0.05,
                "assertion": 0.15
            }
            score += event_type_boosts.get(event.event_type, 0)
            
            # Combine with event's own confidence
            final_score = (score + event.confidence) / 2
            
            scored_matches.append((event, final_score, matched_keywords))
        
        # Sort by score (descending) and return events
        scored_matches.sort(key=lambda x: x[1], reverse=True)
        
        # Return events only (strip scores)
        return [match[0] for match in scored_matches]


class StepEvidence(BaseModel):
    """Evidence for a test step from timeline analysis."""
    found: bool
    confidence: float
    timestamp: Optional[float] = None
    frame_number: Optional[int] = None
    matching_events: List[TimelineEvent] = Field(default_factory=list)
    description: str
    reasoning: str