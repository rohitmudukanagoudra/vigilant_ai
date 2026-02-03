"""Verification Agent - LLM-based semantic verification for test steps.

This agent uses LLM to semantically verify test steps against timeline evidence,
specifically designed to detect false positives by identifying contradictions
between step expectations and actual timeline observations.

Key Features:
- Smart triage to determine when LLM verification is needed
- Adaptive mode: async for <5 steps, batch for >=5 steps
- Contradiction detection for "NOT visible", "NOT available" patterns
- Previous step context for temporal flow understanding
"""

import asyncio
import json
from typing import List, Dict, Any, Tuple, Optional

from analysis_agent.agents.base_agent import BaseAgent
from analysis_agent.core.models import (
    TestStep, VerificationResult, StepStatus,
    AgentDecision, StepEvidence, VideoTimeline
)
from analysis_agent.core.config import Settings


class VerificationAgent(BaseAgent):
    """
    Agent that performs semantic LLM-based verification of test steps.
    Designed to catch false positives by detecting contradictions in evidence.
    """
    
    # Negative observation indicators that suggest potential failure
    NEGATIVE_INDICATORS = [
        "not visible",
        "not available",
        "not present",
        "not found",
        "is missing",
        "does not appear",
        "does not exist",
        "cannot see",
        "cannot find",
        "no longer",
        "fails",
        "failed",
        "failure",
        "assertion failed",
        "not displayed",
        "unavailable",
        "absent",
    ]
    
    def __init__(self, settings: Settings):
        """Initialize verification agent."""
        super().__init__("VERIFICATION", settings)
        self.settings = settings
        self.logger.info("Verification Agent initialized with LLM-based semantic verification")
    
    def needs_llm_verification(
        self,
        step: TestStep,
        evidence: StepEvidence
    ) -> bool:
        """
        Determine if a step needs LLM semantic verification.
        
        Triggers LLM verification when:
        1. Step is an assertion (explicit validation)
        2. Evidence contains negative observations
        3. Confidence is borderline (0.6-0.9)
        4. High confidence but evidence description is ambiguous
        
        Args:
            step: The test step to evaluate
            evidence: Initial evidence from timeline matching
            
        Returns:
            True if LLM verification is recommended
        """
        # Trigger 1: Assertion steps ALWAYS need semantic validation
        if self._is_assertion_step(step):
            self.logger.debug(f"Step {step.step_number}: Assertion step - needs LLM verification")
            return True
        
        # Trigger 2: Evidence contains negative observations
        if self._contains_negative_observations(evidence.description):
            self.logger.debug(f"Step {step.step_number}: Negative observations detected - needs LLM verification")
            return True
        
        if self._contains_negative_observations(evidence.reasoning):
            self.logger.debug(f"Step {step.step_number}: Negative reasoning detected - needs LLM verification")
            return True
        
        # Trigger 3: Borderline confidence (not confident enough to auto-pass)
        if 0.5 <= evidence.confidence < 0.9:
            self.logger.debug(f"Step {step.step_number}: Borderline confidence ({evidence.confidence:.2f}) - needs LLM verification")
            return True
        
        # Trigger 4: No evidence found but not clearly failed
        if not evidence.found and evidence.confidence > 0.3:
            self.logger.debug(f"Step {step.step_number}: Ambiguous evidence - needs LLM verification")
            return True
        
        # Trigger 5: Filter/interaction steps that could have subtle failures
        action_lower = step.action.lower()
        interaction_keywords = ["filter", "select", "apply", "click", "choose", "check", "toggle"]
        if any(kw in action_lower for kw in interaction_keywords):
            self.logger.debug(f"Step {step.step_number}: Interaction step - needs LLM verification")
            return True
        
        return False
    
    def _is_assertion_step(self, step: TestStep) -> bool:
        """Check if step is an assertion/validation step."""
        action_lower = step.action.lower()
        desc_lower = step.description.lower()
        
        assertion_markers = [
            "assertion:",
            "assert that",
            "validate that",
            "verify that",
            "confirm that",
            "ensure that",
            "should be",
            "must be",
            "expect",
        ]
        
        return any(marker in action_lower or marker in desc_lower for marker in assertion_markers)
    
    @staticmethod
    def _contains_negative_observations(text: str) -> bool:
        """
        Detect if text contains negative/missing element phrases.
        
        This is critical for catching false positives where the timeline
        says something is "NOT visible" but keyword matching found it.
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        return any(indicator in text_lower for indicator in VerificationAgent.NEGATIVE_INDICATORS)
    
    async def verify_step_with_timeline_evidence(
        self,
        step: TestStep,
        evidence: StepEvidence,
        previous_results: List[VerificationResult],
        timeline_narrative: str
    ) -> VerificationResult:
        """
        Perform LLM-based semantic verification of a single step.
        
        Uses the timeline evidence and previous step context to determine
        if the step truly passed or if there's a contradiction.
        
        Args:
            step: Test step to verify
            evidence: Initial evidence from timeline matching
            previous_results: Results of previously verified steps (for context)
            timeline_narrative: Overall timeline narrative for context
            
        Returns:
            VerificationResult with LLM-determined status
        """
        self.logger.info(f"🔍 LLM verifying step {step.step_number}: {step.description[:50]}...")
        
        # Build prompt with context
        prompt = self._create_verification_prompt(
            step=step,
            evidence=evidence,
            previous_results=previous_results,
            timeline_narrative=timeline_narrative
        )
        
        try:
            # Make LLM call
            response_text = self.generate_llm_response(prompt=prompt)
            
            # Parse response
            result = self._parse_verification_response(response_text, step, evidence)
            
            self.logger.info(
                f"  Step {step.step_number}: {result.status.value.upper()} "
                f"(confidence: {result.confidence:.2f}, contradiction: "
                f"{'YES' if 'contradiction' in result.evidence.lower() else 'NO'})"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"LLM verification failed for step {step.step_number}: {e}")
            # Fallback to conservative uncertain status
            return self._create_fallback_result(step, evidence, str(e))
    
    async def batch_verify_steps(
        self,
        steps_to_verify: List[Tuple[TestStep, StepEvidence]],
        previous_results: List[VerificationResult],
        timeline_narrative: str
    ) -> List[VerificationResult]:
        """
        Batch verify multiple steps in a single LLM call.
        
        More efficient when verifying 5+ steps. Groups all steps
        into one prompt and parses individual results.
        
        Args:
            steps_to_verify: List of (step, evidence) tuples to verify
            previous_results: Results of code-verified steps (for context)
            timeline_narrative: Overall timeline narrative
            
        Returns:
            List of VerificationResults for each step
        """
        if not steps_to_verify:
            return []
        
        self.logger.info(f"🔍 Batch LLM verifying {len(steps_to_verify)} steps...")
        
        # Build batch prompt
        prompt = self._create_batch_verification_prompt(
            steps_to_verify=steps_to_verify,
            previous_results=previous_results,
            timeline_narrative=timeline_narrative
        )
        
        try:
            # Single LLM call for all steps
            response_text = self.generate_llm_response(prompt=prompt)
            
            # Parse batch response
            results = self._parse_batch_verification_response(
                response_text, steps_to_verify
            )
            
            for result in results:
                self.logger.info(
                    f"  Step {result.step.step_number}: {result.status.value.upper()} "
                    f"(confidence: {result.confidence:.2f})"
                )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch LLM verification failed: {e}")
            # Fallback: create uncertain results for all
            return [
                self._create_fallback_result(step, evidence, str(e))
                for step, evidence in steps_to_verify
            ]
    
    def _create_verification_prompt(
        self,
        step: TestStep,
        evidence: StepEvidence,
        previous_results: List[VerificationResult],
        timeline_narrative: str
    ) -> str:
        """Create LLM prompt for single step verification."""
        
        # Format previous steps context
        prev_context = self._format_previous_results(previous_results[-5:])  # Last 5 steps
        
        # Format matching events
        events_summary = self._format_matching_events(evidence.matching_events[:3])
        
        return f"""You are a test verification expert. Determine if this test step PASSED or FAILED.

**CRITICAL: Detect False Positives**
The timeline may describe events with keywords matching the step, but the step may still have FAILED.
Look carefully for:
- "NOT visible", "NOT available", "NOT present", "is missing" = FAILURE indicators
- "FAILS", "failed", "assertion failed" = Explicit failure
- Contradiction between what step EXPECTS vs what timeline SHOWS

**Test Step #{step.step_number}:**
- Description: {step.description}
- Action: {step.action}
- Expected Outcome: {step.expected_outcome or "Not specified"}

**Timeline Evidence (from video analysis):**
- Evidence Found: {evidence.found}
- Initial Confidence: {evidence.confidence:.2f}
- Description: {evidence.description}
- Reasoning: {evidence.reasoning}

**Matching Timeline Events:**
{events_summary}

**Previous Steps Context (for temporal understanding):**
{prev_context}

**Overall Video Narrative:**
{timeline_narrative[:500]}...

---

**Your Analysis:**
1. What does the step EXPECT to happen?
2. What does the timeline evidence ACTUALLY show happened?
3. Is there a CONTRADICTION between expectation and reality?
4. Are there phrases like "NOT visible", "NOT available", "is missing", "FAILS"?

**Decision Rules:**
- **DEVIATION**: Timeline CONTRADICTS the step (e.g., says "X is NOT visible" when step expects X)
- **OBSERVED**: Timeline CONFIRMS step completed successfully with NO contradictions
- **UNCERTAIN**: Evidence is ambiguous or incomplete

Respond ONLY with valid JSON (no markdown, no extra text):
{{
    "status": "observed|deviation|uncertain",
    "confidence": 0.0-1.0,
    "reasoning": "Your detailed analysis explaining the decision",
    "contradiction_detected": true|false,
    "contradiction_details": "Quote the EXACT text showing contradiction, or null if none"
}}"""
    
    def _create_batch_verification_prompt(
        self,
        steps_to_verify: List[Tuple[TestStep, StepEvidence]],
        previous_results: List[VerificationResult],
        timeline_narrative: str
    ) -> str:
        """Create LLM prompt for batch step verification."""
        
        # Format previous steps context
        prev_context = self._format_previous_results(previous_results[-3:])
        
        # Format all steps
        steps_section = ""
        for i, (step, evidence) in enumerate(steps_to_verify, 1):
            events_summary = self._format_matching_events(evidence.matching_events[:2])
            steps_section += f"""
--- STEP {step.step_number} ---
Description: {step.description}
Action: {step.action}
Evidence Found: {evidence.found}
Confidence: {evidence.confidence:.2f}
Evidence Description: {evidence.description}
Evidence Reasoning: {evidence.reasoning}
Matching Events: {events_summary}
"""
        
        return f"""You are a test verification expert. Analyze MULTIPLE test steps and determine if each PASSED or FAILED.

**CRITICAL: Detect False Positives**
For EACH step, look for:
- "NOT visible", "NOT available", "NOT present" = FAILURE
- "FAILS", "failed", "assertion failed" = Explicit failure
- Contradiction between step EXPECTATION vs timeline REALITY

**Previous Steps Context:**
{prev_context}

**Video Timeline Narrative:**
{timeline_narrative[:400]}...

**STEPS TO VERIFY:**
{steps_section}

---

**For EACH step, determine:**
1. Does timeline CONFIRM or CONTRADICT the step?
2. Any negative phrases indicating failure?

Respond ONLY with valid JSON array (no markdown):
[
    {{
        "step_number": {steps_to_verify[0][0].step_number},
        "status": "observed|deviation|uncertain",
        "confidence": 0.0-1.0,
        "reasoning": "Analysis for this step",
        "contradiction_detected": true|false,
        "contradiction_details": "Exact contradiction text or null"
    }},
    ... (one object per step, in order)
]"""
    
    def _format_previous_results(self, results: List[VerificationResult]) -> str:
        """Format previous verification results for context."""
        if not results:
            return "No previous steps verified yet."
        
        lines = []
        for r in results:
            status_emoji = "✅" if r.status == StepStatus.OBSERVED else "❌" if r.status == StepStatus.DEVIATION else "⚠️"
            lines.append(
                f"Step {r.step.step_number}: {status_emoji} {r.status.value} - {r.step.description[:50]}..."
            )
        return "\n".join(lines)
    
    def _format_matching_events(self, events: list) -> str:
        """Format timeline events for prompt."""
        if not events:
            return "No matching events found."
        
        lines = []
        for e in events:
            lines.append(f"- [{e.timestamp:.1f}s] {e.event_type}: {e.description[:100]}...")
        return "\n".join(lines)
    
    def _parse_verification_response(
        self,
        response_text: str,
        step: TestStep,
        evidence: StepEvidence
    ) -> VerificationResult:
        """Parse LLM response for single step verification."""
        try:
            # Clean response
            cleaned = self._clean_json_response(response_text)
            data = json.loads(cleaned)
            
            # Extract fields
            status_str = data.get("status", "uncertain").lower()
            status = StepStatus(status_str) if status_str in ["observed", "deviation", "uncertain"] else StepStatus.UNCERTAIN
            
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
            
            reasoning = data.get("reasoning", "")
            contradiction = data.get("contradiction_detected", False)
            contradiction_details = data.get("contradiction_details", "")
            
            # Build evidence string
            evidence_str = reasoning
            if contradiction and contradiction_details:
                evidence_str = f"CONTRADICTION DETECTED: {contradiction_details}\n\n{reasoning}"
            
            # Create agent decision
            decision = AgentDecision(
                agent_name="VerificationAgent",
                decision=status.value.upper(),
                reasoning=reasoning,
                confidence=confidence,
                metadata={
                    "contradiction_detected": contradiction,
                    "contradiction_details": contradiction_details,
                    "llm_verified": True
                }
            )
            
            return VerificationResult(
                step=step,
                status=status,
                confidence=confidence,
                video_timestamp=evidence.timestamp,
                evidence=evidence_str,
                ocr_detected_text=[],
                vision_analysis=evidence.description,
                agent_decisions=[decision],
                notes=f"LLM-verified. Contradiction: {'Yes' if contradiction else 'No'}"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to parse LLM response: {e}")
            return self._create_fallback_result(step, evidence, f"Parse error: {e}")
    
    def _parse_batch_verification_response(
        self,
        response_text: str,
        steps_to_verify: List[Tuple[TestStep, StepEvidence]]
    ) -> List[VerificationResult]:
        """Parse LLM response for batch step verification."""
        try:
            # Clean response
            cleaned = self._clean_json_response(response_text)
            data_list = json.loads(cleaned)
            
            if not isinstance(data_list, list):
                raise ValueError("Expected JSON array")
            
            results = []
            
            # Match results to steps by index (in order)
            for i, (step, evidence) in enumerate(steps_to_verify):
                if i < len(data_list):
                    data = data_list[i]
                    
                    status_str = data.get("status", "uncertain").lower()
                    status = StepStatus(status_str) if status_str in ["observed", "deviation", "uncertain"] else StepStatus.UNCERTAIN
                    
                    confidence = float(data.get("confidence", 0.5))
                    confidence = max(0.0, min(1.0, confidence))
                    
                    reasoning = data.get("reasoning", "")
                    contradiction = data.get("contradiction_detected", False)
                    contradiction_details = data.get("contradiction_details", "")
                    
                    evidence_str = reasoning
                    if contradiction and contradiction_details:
                        evidence_str = f"CONTRADICTION DETECTED: {contradiction_details}\n\n{reasoning}"
                    
                    decision = AgentDecision(
                        agent_name="VerificationAgent",
                        decision=status.value.upper(),
                        reasoning=reasoning,
                        confidence=confidence,
                        metadata={
                            "contradiction_detected": contradiction,
                            "llm_verified": True,
                            "batch_verified": True
                        }
                    )
                    
                    results.append(VerificationResult(
                        step=step,
                        status=status,
                        confidence=confidence,
                        video_timestamp=evidence.timestamp,
                        evidence=evidence_str,
                        ocr_detected_text=[],
                        vision_analysis=evidence.description,
                        agent_decisions=[decision],
                        notes="Batch LLM-verified"
                    ))
                else:
                    # Fallback if LLM didn't return enough results
                    results.append(self._create_fallback_result(step, evidence, "Missing in batch response"))
            
            return results
            
        except Exception as e:
            self.logger.warning(f"Failed to parse batch LLM response: {e}")
            return [
                self._create_fallback_result(step, evidence, f"Batch parse error: {e}")
                for step, evidence in steps_to_verify
            ]
    
    def _clean_json_response(self, response_text: str) -> str:
        """Clean LLM response to extract JSON."""
        import re
        
        if not response_text or not response_text.strip():
            raise ValueError("Empty response from LLM")
        
        text = response_text.strip()
        
        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        # Find JSON start/end
        if "[" in text and (text.find("[") < text.find("{") or "{" not in text):
            start = text.find("[")
            end = text.rfind("]") + 1
        else:
            start = text.find("{")
            end = text.rfind("}") + 1
        
        if start >= 0 and end > start:
            text = text[start:end]
        
        # Fix single quotes to double quotes for JSON keys/values
        text = re.sub(r"(?<![\\])'", '"', text)
        
        # Remove trailing commas
        text = re.sub(r',\s*([}\]])', r'\1', text)
        
        return text
    
    def _create_fallback_result(
        self,
        step: TestStep,
        evidence: StepEvidence,
        error_message: str
    ) -> VerificationResult:
        """Create a fallback uncertain result when LLM verification fails."""
        return VerificationResult(
            step=step,
            status=StepStatus.UNCERTAIN,
            confidence=0.5,
            video_timestamp=evidence.timestamp if evidence else None,
            evidence=f"LLM verification failed: {error_message}. Using conservative uncertain status.",
            ocr_detected_text=[],
            vision_analysis=evidence.description if evidence else None,
            agent_decisions=[
                AgentDecision(
                    agent_name="VerificationAgent",
                    decision="UNCERTAIN",
                    reasoning=f"Fallback due to: {error_message}",
                    confidence=0.5,
                    metadata={"fallback": True, "error": error_message}
                )
            ],
            notes="Fallback result due to LLM error"
        )