"""Planning Agent - Determines optimal verification strategy."""

from typing import Dict, Any
import json


from analysis_agent.agents.base_agent import BaseAgent
from analysis_agent.core.models import VerificationStrategy, PlanningLog
from analysis_agent.core.config import Settings


class PlanningAgent(BaseAgent):
    """
    Agent that analyzes test requirements and creates verification strategy.
    Uses LLM reasoning to adapt strategy based on test complexity.
    """
    
    def __init__(self, settings: Settings):
        """Initialize planning agent."""
        super().__init__("PLANNING", settings)
        self.settings = settings
        self.logger.info("Planning Agent initialized")
    
    async def create_strategy(
        self,
        planning_log: PlanningLog,
        video_duration: float
    ) -> VerificationStrategy:
        """
        Create adaptive verification strategy based on test characteristics.
        
        Args:
            planning_log: The parsed planning log
            video_duration: Duration of the video in seconds
            
        Returns:
            VerificationStrategy with optimized parameters
        """
        self.logger.info("Analyzing test complexity...")
        
        # Assess test complexity
        complexity_score = self._assess_complexity(planning_log, video_duration)
        
        # Create prompt for strategy planning
        prompt = f"""You are a test verification planning expert. Analyze this test scenario and create an optimal verification strategy.

Test Information:
- Total Steps: {len(planning_log.steps)}
- Video Duration: {video_duration:.2f} seconds
- Complexity Score: {complexity_score}/10

Steps Overview:
{self._format_steps(planning_log.steps[:5])}
{"... and more" if len(planning_log.steps) > 5 else ""}

Current Configuration:
- Frame Interval: {self.settings.frame_extraction_interval}s
- Max Frames: {self.settings.max_frames_per_video}
- Batch Size: {self.settings.vision_batch_size}

Based on this information, determine the OPTIMAL strategy:

1. **Frame Interval** (1-5 seconds): How often to extract frames?
   - Lower = more frames, higher accuracy, more API calls
   - Higher = fewer frames, faster, lower cost
   
2. **Max Frames** (10-100): Maximum frames to analyze?
   - Consider video duration and step count
   
3. **Use Batch Processing** (true/false): Process frames in batches?
   - Batch = faster but less granular
   - Sequential = slower but more precise
   
4. **Confidence Threshold** (0.6-0.95): Minimum confidence for OBSERVED status?
   - Lower = more lenient, fewer UNCERTAINs
   - Higher = stricter, more accurate
   
5. **Priority Mode** ("vision", "ocr", "hybrid"): Which analysis to prioritize?
   - vision = Better for UI changes, clicks
   - ocr = Better for text-heavy tests
   - hybrid = Best overall accuracy (recommended)

Respond in this JSON format:
{{
    "frame_interval": <number>,
    "max_frames": <number>,
    "use_batch_processing": <boolean>,
    "confidence_threshold": <number>,
    "priority_mode": "<vision|ocr|hybrid>",
    "reasoning": "<explain your strategy choices>"
}}

Focus on best efficient breakdown that would provide rich insights."""

        try:
            # Get LLM decision
            response_text = self.generate_llm_response(prompt)
            
            # Parse JSON response
            cleaned_text = response_text.strip()
            # Remove markdown code blocks if present
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[1].split("```")[0].strip()
            
             # Additional cleanup for potential prefixes/suffixes
            if not cleaned_text.startswith("{") and "{" in cleaned_text:
                cleaned_text = cleaned_text[cleaned_text.find("{"):]
            if not cleaned_text.endswith("}") and "}" in cleaned_text:
                cleaned_text = cleaned_text[:cleaned_text.rfind("}")+1]
            
            strategy_dict = json.loads(cleaned_text)
            
            # Ensure frame_interval is an integer
            if 'frame_interval' in strategy_dict:
                strategy_dict['frame_interval'] = int(strategy_dict['frame_interval'])

            strategy = VerificationStrategy(**strategy_dict)
            
            self.logger.info(f"Strategy created - {strategy.priority_mode} mode")
            self.logger.info(f"  Frame interval: {strategy.frame_interval}s")
            self.logger.info(f"  Max frames: {strategy.max_frames}")
            self.logger.info(f"  Confidence threshold: {strategy.confidence_threshold}")
            self.logger.info(f"  Reasoning: {strategy.reasoning[:100]}...")
            
            return strategy
            
        except Exception as e:
            self.logger.warning(f"Failed to create custom strategy, using defaults: {e}")
            # Fallback to default strategy
            return VerificationStrategy(
                frame_interval=self.settings.frame_extraction_interval,
                max_frames=self.settings.max_frames_per_video,
                use_batch_processing=True,
                confidence_threshold=0.7,
                priority_mode="hybrid",
                reasoning="Default strategy due to planning error"
            )
    
    def _assess_complexity(self, planning_log: PlanningLog, video_duration: float) -> float:
        """
        Assess test complexity on a scale of 1-10.
        
        Factors:
        - Number of steps
        - Video duration
        - Step descriptions (keywords indicating complexity)
        """
        score = 5.0  # Base score
        
        # Step count factor
        step_count = len(planning_log.steps)
        if step_count > 20:
            score += 2
        elif step_count > 10:
            score += 1
        elif step_count < 5:
            score -= 1
        
        # Duration factor
        if video_duration > 120:  # > 2 minutes
            score += 1
        elif video_duration < 30:  # < 30 seconds
            score -= 1
        
        # Complexity keywords
        complex_keywords = ['validate', 'verify', 'check', 'wait', 'scroll', 'drag', 'hover']
        simple_keywords = ['click', 'type', 'navigate']
        
        for step in planning_log.steps:
            desc_lower = step.description.lower()
            if any(kw in desc_lower for kw in complex_keywords):
                score += 0.2
            if any(kw in desc_lower for kw in simple_keywords):
                score -= 0.1
        
        # Clamp between 1-10
        return max(1.0, min(10.0, score))
    
    def _format_steps(self, steps: list) -> str:
        """Format steps for display in prompt."""
        return "\n".join([
            f"{i+1}. {step.description}"
            for i, step in enumerate(steps)
        ])