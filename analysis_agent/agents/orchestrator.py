"""Orchestrator Agent - Master coordinator for the multi-agent system.

This is the central coordination point that manages the complete verification workflow:
1. Planning - Create verification strategy
2. Frame Extraction - Extract frames from video
3. Key Frame Selection - Select representative frames
4. OCR Analysis - Extract text from frames
5. Comprehensive Vision Analysis - Single-pass video understanding
6. Smart Verification - LLM verification for semantic validation
7. Report Generation - Create deviation report

Key Innovation:
- Smart Triage: Decides when LLM verification is needed vs code-based verification
- Adaptive Mode: Async verification for <5 steps, batch for >=5 steps
- Contradiction Detection: LLM catches false positives from keyword matching
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, Any, Callable, List, Tuple
from datetime import datetime
import cv2

from analysis_agent.agents.base_agent import BaseAgent
from analysis_agent.core.models import (
    PlanningLog, TestOutput, DeviationReport, VerificationResult,
    VideoFrame, TaskProgress, TaskStatus, StepStatus, AgentMetrics,
    TestStep, StepEvidence, VideoTimeline
)
from analysis_agent.core.config import Settings
from analysis_agent.agents.planning_agent import PlanningAgent
from analysis_agent.agents.comprehensive_vision_agent import ComprehensiveVisionAgent
from analysis_agent.agents.ocr_agent import OCRAgent
from analysis_agent.agents.verification_agent import VerificationAgent


class OrchestratorAgent(BaseAgent):
    """
    Master agent that coordinates all other agents.
    Manages the complete verification workflow with intelligent orchestration.
    """
    
    def __init__(self, settings: Settings):
        """Initialize orchestrator and all sub-agents."""
        super().__init__("ORCHESTRATOR", settings)
        self.settings = settings
        self.planning_agent = PlanningAgent(settings)
        self.comprehensive_vision = ComprehensiveVisionAgent(settings)
        self.ocr_agent = OCRAgent(settings)
        self.verification_agent = VerificationAgent(settings)
        self.logger.info("Orchestrator initialized with Smart Verification architecture")
        self.progress_callback = None
    
    def emit_progress(
        self,
        *,
        status: TaskStatus,
        progress: float,
        phase: str,
        step: str,
        message: str,
        error: str = None
    ):
        """
        Centralized progress emission with best-practice contract.
        
        This is the single source of truth for all progress updates.
        Ensures consistent format, monotonic progress, and proper logging.
        
        Args:
            status: Task status (PROCESSING, COMPLETED, FAILED)
            progress: Progress value (will be clamped to 0.0-1.0)
            phase: Machine-readable phase identifier
            step: Human-readable step name (UI headline)
            message: Detailed human-readable message
            error: Optional error message
        """
        # HARD CLAMP: Ensure progress is always between 0.0 and 1.0
        progress = max(0.0, min(progress, 1.0))
        
        # Log with consistent format
        self.logger.info(
            f"📊 [{phase.upper()}] {progress:.0%} | {step} — {message}"
        )
        
        # Emit to callback if available
        if self.progress_callback:
            try:
                self.progress_callback(TaskProgress(
                    task_id="current",
                    status=status,
                    progress=progress,
                    phase=phase,
                    current_step=step,
                    message=message,
                    error=error
                ))
            except Exception as e:
                self.logger.error(f"❌ Failed to send progress update: {e}", exc_info=True)
        else:
            self.logger.debug("Progress callback not set - update not sent to UI")
    
    async def execute_verification(
        self,
        planning_log: PlanningLog,
        test_output: TestOutput,
        video_path: Path,
        temp_dir: Path,
        progress_callback: Callable[[TaskProgress], None] = None
    ) -> DeviationReport:
        """
        Execute complete verification workflow with all agents.
        
        Args:
            planning_log: Parsed planning log
            test_output: Parsed test output
            video_path: Path to video file
            temp_dir: Temporary directory for frames
            progress_callback: Optional callback for progress updates
            
        Returns:
            Complete deviation report with metrics
        """
        overall_start = time.time()
        all_metrics: List[AgentMetrics] = []
        self.progress_callback = progress_callback
        current_progress = 0.0
        
        try:
            # Phase 1: Planning (5%)
            current_progress = 0.05
            self.emit_progress(
                status=TaskStatus.PROCESSING,
                progress=0.05,
                phase="planning",
                step="Planning",
                message="Creating verification strategy..."
            )
            self.logger.info("=== Phase 1: Strategic Planning ===")
            
            with self.timed_operation("Planning Phase"):
                phase_start = time.time()
                llm_start = self.planning_agent.llm_calls
                
                video_duration = self._get_video_duration(video_path)
                strategy = await self.planning_agent.create_strategy(planning_log, video_duration)
                
                planning_metrics = self.planning_agent.create_metrics(
                    phase="Planning",
                    time_taken=time.time() - phase_start,
                    llm_calls=self.planning_agent.llm_calls - llm_start
                )
                all_metrics.append(planning_metrics)
            
            # Phase 2: Frame Extraction (15%)
            current_progress = 0.15
            self.emit_progress(
                status=TaskStatus.PROCESSING,
                progress=0.15,
                phase="extraction",
                step="Frame Extraction",
                message="Extracting video frames..."
            )
            self.logger.info("=== Phase 2: Frame Extraction ===")
            
            with self.timed_operation("Frame Extraction"):
                phase_start = time.time()
                all_frames = await asyncio.to_thread(
                    self._extract_frames, video_path, temp_dir, strategy
                )
                
                extraction_metrics = self.create_metrics(
                    phase="Frame Extraction",
                    time_taken=time.time() - phase_start,
                    llm_calls=0
                )
                all_metrics.append(extraction_metrics)
                self.logger.info(f"Extracted {len(all_frames)} frames")
            
            # Phase 3: Select Key Frames (20%)
            current_progress = 0.20
            self.emit_progress(
                status=TaskStatus.PROCESSING,
                progress=0.20,
                phase="key_frames",
                step="Key Frame Selection",
                message="Selecting key frames..."
            )
            self.logger.info("=== Phase 3: Key Frame Selection ===")
            
            key_frames = await asyncio.to_thread(
                self.comprehensive_vision.extract_key_frames,
                all_frames, 
                max_key_frames=15
            )
            self.logger.info(f"Selected {len(key_frames)} key frames from {len(all_frames)} total")
            
            # Phase 4: OCR Analysis on Key Frames (30%)
            current_progress = 0.30
            self.emit_progress(
                status=TaskStatus.PROCESSING,
                progress=0.30,
                phase="ocr",
                step="OCR Analysis",
                message="Analyzing text in key frames..."
            )
            self.logger.info("=== Phase 4: OCR Analysis (Key Frames Only) ===")
            
            with self.timed_operation("OCR Analysis"):
                phase_start = time.time()
                llm_start = self.ocr_agent.llm_calls
                
                key_frames_with_ocr = await asyncio.to_thread(
                    self.ocr_agent.analyze_frames, key_frames
                )
                ocr_data = {f.frame_number: f.ocr_text for f in key_frames_with_ocr}
                
                ocr_metrics = self.ocr_agent.create_metrics(
                    phase="OCR Analysis",
                    time_taken=time.time() - phase_start,
                    llm_calls=self.ocr_agent.llm_calls - llm_start
                )
                all_metrics.append(ocr_metrics)
            
            # Phase 5: Comprehensive Video Analysis (30-60%) - SINGLE PASS
            current_progress = 0.30
            self.emit_progress(
                status=TaskStatus.PROCESSING,
                progress=0.30,
                phase="vision",
                step="Comprehensive Vision Analysis",
                message="Starting comprehensive video analysis..."
            )
            self.logger.info("=== Phase 5: Comprehensive Vision Analysis (Single Pass) ===")
            
            vision_progress_state = {"current": 0.30, "last_update": time.time(), "ai_start": None}
            
            def vision_progress_callback(message: str):
                """Nested callback for vision analysis progress."""
                nonlocal current_progress
                current_time = time.time()
                
                if "Creating" in message or "prompt" in message:
                    vision_progress_state["current"] = 0.35
                elif "Preparing" in message:
                    vision_progress_state["current"] = 0.38
                elif "Analyzing" in message or "AI" in message:
                    vision_progress_state["current"] = 0.40
                    vision_progress_state["ai_start"] = current_time
                elif "Parsing" in message or "timeline" in message:
                    vision_progress_state["current"] = 0.58
                elif "complete" in message.lower():
                    vision_progress_state["current"] = 0.60
                
                vision_progress_state["last_update"] = current_time
                current_progress = vision_progress_state["current"]
                self.emit_progress(
                    status=TaskStatus.PROCESSING,
                    progress=vision_progress_state["current"],
                    phase="vision",
                    step="Comprehensive Vision Analysis",
                    message=message
                )
            
            async def run_vision_with_progress():
                """Run vision analysis with periodic progress nudges."""
                vision_task = asyncio.create_task(
                    self.comprehensive_vision.analyze_video_comprehensive(
                        key_frames=key_frames_with_ocr,
                        test_steps=planning_log.steps,
                        ocr_data=ocr_data,
                        progress_callback=vision_progress_callback
                    )
                )
                
                poll_interval = 1.0
                last_progress_update = time.time()
                
                while not vision_task.done():
                    await asyncio.sleep(poll_interval)
                    
                    if not vision_task.done():
                        current_time = time.time()
                        ai_start = vision_progress_state.get("ai_start")
                        
                        if 0.40 <= vision_progress_state["current"] < 0.58 and ai_start:
                            elapsed = current_time - ai_start
                            
                            if current_time - last_progress_update >= 2.0:
                                vision_progress_state["current"] = min(
                                    0.58,
                                    vision_progress_state["current"] + 0.01
                                )
                                dots = "." * int((elapsed % 4) + 1)
                                message = f"AI analyzing video frames{dots} ({int(elapsed)}s elapsed)"
                                current_progress = vision_progress_state["current"]
                                self.emit_progress(
                                    status=TaskStatus.PROCESSING,
                                    progress=vision_progress_state["current"],
                                    phase="vision",
                                    step="AI Video Understanding",
                                    message=message
                                )
                                last_progress_update = current_time
                
                return await vision_task
            
            with self.timed_operation("Comprehensive Vision Analysis"):
                phase_start = time.time()
                llm_start = self.comprehensive_vision.llm_calls
                
                timeline = await run_vision_with_progress()
                
                current_progress = 0.60
                self.emit_progress(
                    status=TaskStatus.PROCESSING,
                    progress=0.60,
                    phase="vision",
                    step="Vision Analysis Complete",
                    message="Vision analysis complete"
                )
                
                vision_metrics = self.comprehensive_vision.create_metrics(
                    phase="Vision Analysis",
                    time_taken=time.time() - phase_start,
                    llm_calls=self.comprehensive_vision.llm_calls - llm_start
                )
                all_metrics.append(vision_metrics)
                
                self.logger.info(f"Timeline created: {timeline.narrative[:100]}...")
                self.logger.info(f"Events captured: {len(timeline.events)}")
            
            # Phase 6: Smart Step Verification (60-95%) - WITH LLM TRIAGE
            current_progress = 0.60
            self.emit_progress(
                status=TaskStatus.PROCESSING,
                progress=0.60,
                phase="verification",
                step="Smart Verification",
                message="Starting smart step verification..."
            )
            self.logger.info("=== Phase 6: Smart Step Verification (LLM Triage) ===")
            
            with self.timed_operation("Smart Verification Phase"):
                phase_start = time.time()
                llm_start = self.verification_agent.llm_calls
                
                def verification_progress_callback(step_num: int, total_steps: int, description: str):
                    nonlocal current_progress
                    progress_pct = 0.60 + (0.35 * step_num / total_steps)
                    current_progress = progress_pct
                    self.emit_progress(
                        status=TaskStatus.PROCESSING,
                        progress=progress_pct,
                        phase="verification",
                        step="Smart Verification",
                        message=f"Verifying step {step_num}/{total_steps}: {description[:50]}..."
                    )
                
                verification_results = await self._smart_verify_steps(
                    steps=planning_log.steps,
                    timeline=timeline,
                    ocr_data=ocr_data,
                    progress_callback=verification_progress_callback
                )
                
                verification_metrics = self.verification_agent.create_metrics(
                    phase="Verification",
                    time_taken=time.time() - phase_start,
                    llm_calls=self.verification_agent.llm_calls - llm_start
                )
                all_metrics.append(verification_metrics)
                
                llm_verified_count = sum(
                    1 for r in verification_results 
                    if any(d.metadata.get("llm_verified") for d in r.agent_decisions)
                )
                self.logger.info(
                    f"Verification complete: {llm_verified_count}/{len(verification_results)} "
                    f"steps LLM-verified"
                )
            
            # Phase 7: Report Generation (95%)
            current_progress = 0.95
            self.emit_progress(
                status=TaskStatus.PROCESSING,
                progress=0.95,
                phase="reporting",
                step="Report Generation",
                message="Generating report..."
            )
            self.logger.info("=== Phase 7: Report Generation ===")
            
            with self.timed_operation("Report Generation"):
                report = self._generate_report(
                    test_output, verification_results, planning_log, strategy, all_metrics
                )
            
            # Complete (100%)
            total_time = time.time() - overall_start
            total_llm = sum(m.llm_calls for m in all_metrics)
            
            self.logger.info(f"Verification complete in {total_time:.2f}s")
            self.logger.info(f"Total LLM calls: {total_llm}")
            self.logger.info(f"Result: {report.overall_status} ({report.pass_rate:.1f}% pass rate)")
            
            current_progress = 1.0
            self.emit_progress(
                status=TaskStatus.COMPLETED,
                progress=1.0,
                phase="complete",
                step="Analysis Complete",
                message="Verification finished successfully"
            )
            
            return report
            
        except Exception as e:
            self.logger.error(f"Verification failed: {e}", exc_info=True)
            self.emit_progress(
                status=TaskStatus.FAILED,
                progress=current_progress,
                phase="error",
                step="Error",
                message=str(e),
                error=str(e)
            )
            raise
    
    async def _smart_verify_steps(
        self,
        steps: List[TestStep],
        timeline: VideoTimeline,
        ocr_data: Dict[int, List[str]],
        progress_callback: Callable = None
    ) -> List[VerificationResult]:
        """
        Smart verification with LLM triage.
        
        Flow:
        1. Get initial evidence for ALL steps (code-based, fast)
        2. Triage: Identify which steps need LLM verification
        3. Code-based results for simple cases
        4. LLM verification for uncertain/assertion/contradiction cases
        5. Adaptive mode: async for <5 steps, batch for >=5
        
        Args:
            steps: Test steps to verify
            timeline: Video timeline from comprehensive analysis
            ocr_data: OCR results by frame number
            progress_callback: Progress update callback
            
        Returns:
            List of verification results for all steps
        """
        self.logger.info("=" * 80)
        self.logger.info("SMART VERIFICATION - Step-by-Step Analysis with LLM Triage")
        self.logger.info("=" * 80)
        
        # Step 1: Get initial evidence for ALL steps
        initial_evidence: List[Tuple[TestStep, StepEvidence]] = []
        previous_timestamp = None
        
        for i, step in enumerate(steps):
            self.logger.info(f"\n📍 Gathering evidence for step {i+1}/{len(steps)}")
            self.logger.info(f"   Description: {step.description}")
            
            evidence = self.comprehensive_vision.verify_step_against_timeline(
                step=step,
                timeline=timeline,
                ocr_data=ocr_data,
                previous_step_timestamp=previous_timestamp
            )
            
            initial_evidence.append((step, evidence))
            
            if evidence.found and evidence.timestamp is not None:
                previous_timestamp = evidence.timestamp
            
            self.logger.info(f"   Evidence found: {evidence.found}, Confidence: {evidence.confidence:.2f}")
        
        # Step 2: Smart Triage - identify which need LLM verification
        needs_llm: List[Tuple[TestStep, StepEvidence]] = []
        code_based: List[Tuple[TestStep, StepEvidence]] = []
        
        for step, evidence in initial_evidence:
            if self.verification_agent.needs_llm_verification(step, evidence):
                needs_llm.append((step, evidence))
                self.logger.info(f"   ⚡ Step {step.step_number}: Flagged for LLM verification")
            else:
                code_based.append((step, evidence))
                self.logger.info(f"   ✓ Step {step.step_number}: Code-based verification sufficient")
        
        self.logger.info(f"\nTriage Result: {len(code_based)} code-based, {len(needs_llm)} LLM-verified")
        
        # Step 3: Create code-based results
        code_results = []
        for step, evidence in code_based:
            result = self._create_result_from_evidence(step, evidence, ocr_data)
            code_results.append(result)
        
        # Step 4: LLM verification for flagged steps
        llm_results = []
        if needs_llm:
            self.logger.info(f"\n🔍 Starting LLM verification for {len(needs_llm)} steps...")
            
            if len(needs_llm) < 5:
                # Async per-step verification
                self.logger.info("   Mode: Async per-step (< 5 steps)")
                llm_results = await self._verify_steps_async(
                    needs_llm, code_results, timeline.narrative, progress_callback
                )
            else:
                # Batch verification
                self.logger.info("   Mode: Batch verification (>= 5 steps)")
                llm_results = await self.verification_agent.batch_verify_steps(
                    steps_to_verify=needs_llm,
                    previous_results=code_results,
                    timeline_narrative=timeline.narrative
                )
        
        # Step 5: Merge and order results by step number
        all_results = code_results + llm_results
        all_results.sort(key=lambda r: r.step.step_number)
        
        # Log final results
        self.logger.info("\n" + "=" * 80)
        self.logger.info("VERIFICATION COMPLETE - Summary")
        self.logger.info("=" * 80)
        for result in all_results:
            symbol = "✅" if result.status == StepStatus.OBSERVED else \
                    "❌" if result.status == StepStatus.DEVIATION else "⚠️"
            llm_tag = "[LLM]" if any(d.metadata.get("llm_verified") for d in result.agent_decisions) else "[CODE]"
            self.logger.info(
                f"   Step {result.step.step_number}: {symbol} {result.status.value.upper()} "
                f"{llm_tag} (confidence: {result.confidence:.2f})"
            )
        
        return all_results
    
    async def _verify_steps_async(
        self,
        steps_to_verify: List[Tuple[TestStep, StepEvidence]],
        previous_results: List[VerificationResult],
        timeline_narrative: str,
        progress_callback: Callable = None
    ) -> List[VerificationResult]:
        """
        Verify steps asynchronously, one at a time.
        
        Used when there are fewer than 5 steps to verify.
        Each step gets its own LLM call with context from previous results.
        """
        results = []
        accumulated_results = list(previous_results)  # Start with code-based results
        
        for i, (step, evidence) in enumerate(steps_to_verify):
            if progress_callback:
                progress_callback(
                    step.step_number,
                    len(steps_to_verify) + len(previous_results),
                    step.description
                )
            
            result = await self.verification_agent.verify_step_with_timeline_evidence(
                step=step,
                evidence=evidence,
                previous_results=accumulated_results,
                timeline_narrative=timeline_narrative
            )
            
            results.append(result)
            accumulated_results.append(result)  # Add to context for next step
        
        return results
    
    def _create_result_from_evidence(
        self,
        step: TestStep,
        evidence: StepEvidence,
        ocr_data: Dict[int, List[str]]
    ) -> VerificationResult:
        """
        Create verification result from code-based evidence.
        
        Used for simple cases where LLM verification is not needed.
        """
        # Determine status based on confidence thresholds
        if evidence.confidence >= 0.85:
            status = StepStatus.OBSERVED
        elif evidence.confidence >= 0.5:
            status = StepStatus.UNCERTAIN
        else:
            status = StepStatus.DEVIATION
        
        # Get OCR matches for this frame
        ocr_matches = []
        if evidence.frame_number:
            ocr_matches = ocr_data.get(evidence.frame_number, [])
        
        return VerificationResult(
            step=step,
            status=status,
            confidence=evidence.confidence,
            video_timestamp=evidence.timestamp,
            evidence=evidence.reasoning,
            ocr_detected_text=list(ocr_matches),
            vision_analysis=evidence.description,
            agent_decisions=[],
            notes="Code-based verification (no LLM)"
        )
    
    def _extract_frames(self, video_path: Path, temp_dir: Path, strategy) -> List[VideoFrame]:
        """Extract frames from video based on strategy."""
        frames = []
        frames_dir = temp_dir / "frames"
        frames_dir.mkdir(exist_ok=True)
        
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        frame_interval = int(fps * strategy.frame_interval)
        frame_count = 0
        saved_count = 0
        
        while cap.isOpened() and saved_count < strategy.max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                timestamp = frame_count / fps
                frame_filename = f"frame_{saved_count:04d}_{timestamp:.3f}s.jpg"
                frame_path = frames_dir / frame_filename
                
                cv2.imwrite(str(frame_path), frame)
                
                frames.append(VideoFrame(
                    frame_number=saved_count,
                    timestamp=timestamp,
                    frame_path=str(frame_path)
                ))
                
                saved_count += 1
            
            frame_count += 1
        
        cap.release()
        return frames
    
    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds."""
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
        return duration
    
    def _extract_keywords(self, description: str) -> List[str]:
        """Extract keywords from step description."""
        import re
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        words = description.lower().split()
        keywords = [w.strip('.,!?;:') for w in words if w.lower() not in stop_words and len(w) > 2]
        
        # Also extract quoted strings
        quoted = re.findall(r'"([^"]*)"', description)
        keywords.extend(quoted)
        
        return keywords
    
    def _generate_report(
        self,
        test_output: TestOutput,
        verification_results: List[VerificationResult],
        planning_log: PlanningLog,
        strategy,
        all_metrics: List[AgentMetrics]
    ) -> DeviationReport:
        """Generate final deviation report with metrics."""
        observed = sum(1 for r in verification_results if r.status == StepStatus.OBSERVED)
        deviated = sum(1 for r in verification_results if r.status == StepStatus.DEVIATION)
        uncertain = sum(1 for r in verification_results if r.status == StepStatus.UNCERTAIN)
        
        if deviated == 0 and uncertain == 0:
            overall_status = "PASSED"
            summary = "All test steps were successfully verified with high confidence."
        elif deviated > 0:
            overall_status = "FAILED"
            summary = f"{deviated} step(s) showed deviations from planned execution."
        else:
            overall_status = "UNCERTAIN"
            summary = f"{uncertain} step(s) could not be verified with high confidence."
        
        # Calculate totals from metrics
        total_time = sum(m.time_taken for m in all_metrics)
        total_llm_calls = sum(m.llm_calls for m in all_metrics)
        
        # Create phase breakdown
        phase_metrics = {}
        for metric in all_metrics:
            if metric.phase not in phase_metrics:
                phase_metrics[metric.phase] = {"time": 0.0, "llm_calls": 0}
            phase_metrics[metric.phase]["time"] += metric.time_taken
            phase_metrics[metric.phase]["llm_calls"] += metric.llm_calls
        
        return DeviationReport(
            test_name=test_output.test_name,
            execution_date=datetime.now(),
            total_steps=len(verification_results),
            observed_steps=observed,
            deviated_steps=deviated,
            uncertain_steps=uncertain,
            verification_results=verification_results,
            strategy_used=strategy,
            summary=summary,
            overall_status=overall_status,
            metadata={
                "test_status": test_output.status,
                "test_duration": test_output.duration
            },
            agent_metrics=all_metrics,
            execution_time=total_time,
            total_llm_calls=total_llm_calls,
            phase_metrics=phase_metrics
        )