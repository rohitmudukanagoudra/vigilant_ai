"""Comprehensive Vision Agent - Single-pass video analysis.

This agent analyzes the ENTIRE video in ONE comprehensive pass, creating a rich
timeline of events that can be used for step verification.

Key Innovation:
- Single detailed LLM call analyzing entire video narrative
- Creates timeline with events, UI elements, and text observations
- Timeline is used by VerificationAgent for semantic step validation

Architecture:
1. Extract 10-15 key frames (strategic sampling)
2. Single comprehensive LLM call analyzing video narrative
3. Return timeline for VerificationAgent to validate steps

Note: Actual step verification (pass/fail determination) is delegated to
VerificationAgent which uses LLM-based semantic analysis for accuracy.
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import re


from analysis_agent.agents.base_agent import BaseAgent
from analysis_agent.core.models import (
    VideoFrame, TestStep, VideoTimeline, TimelineEvent,
    StepEvidence, StepStatus
)
from analysis_agent.core.config import Settings


class ComprehensiveVisionAgent(BaseAgent):
    """
    Agent that analyzes entire video in ONE comprehensive pass.
    Creates a rich timeline of all events for step verification.
    """
    
    def __init__(self, settings: Settings):
        """Initialize comprehensive vision agent."""
        super().__init__("COMPREHENSIVE_VISION", settings)
        self.settings = settings
        self.logger.info("Comprehensive Vision Agent initialized")
    
    def extract_key_frames(
        self,
        all_frames: List[VideoFrame],
        max_key_frames: int = 15
    ) -> List[VideoFrame]:
        """
        Extract key frames using strategic sampling.
        
        Strategy:
        - Always include first and last frames
        - Sample evenly across video duration
        - TODO: Add scene change detection for better frame selection
        
        Args:
            all_frames: All extracted frames
            max_key_frames: Maximum number of key frames to extract
            
        Returns:
            List of strategically selected key frames
        """
        if len(all_frames) <= max_key_frames:
            self.logger.info(f"Using all {len(all_frames)} frames as key frames")
            return all_frames
        
        key_frames = []
        
        # Always include first frame
        key_frames.append(all_frames[0])
        
        # Sample evenly across middle frames
        step = len(all_frames) / (max_key_frames - 1)
        for i in range(1, max_key_frames - 1):
            idx = int(i * step)
            if idx < len(all_frames):
                key_frames.append(all_frames[idx])
        
        # Always include last frame
        if all_frames[-1] not in key_frames:
            key_frames.append(all_frames[-1])
        
        self.logger.info(
            f"Extracted {len(key_frames)} key frames from {len(all_frames)} total "
            f"(timestamps: {key_frames[0].timestamp:.1f}s - {key_frames[-1].timestamp:.1f}s)"
        )
        
        return key_frames
    
    async def analyze_video_comprehensive(
        self,
        key_frames: List[VideoFrame],
        test_steps: List[TestStep],
        ocr_data: Dict[int, List[str]],
        progress_callback=None
    ) -> VideoTimeline:
        """
        Perform single comprehensive analysis of entire video.
        
        This is the CORE INNOVATION: ONE detailed analysis instead of
        multiple per-step analyses.
        
        Args:
            key_frames: Strategically selected key frames
            test_steps: Test steps for context
            ocr_data: OCR results mapped by frame number
            progress_callback: Optional callback for progress updates
            
        Returns:
            VideoTimeline with comprehensive event narrative
        """
        self.logger.info(
            f"🎬 Starting comprehensive video analysis "
            f"({len(key_frames)} frames, {len(test_steps)} steps)"
        )
        
        # Prepare frame paths for vision API
        frame_paths = [str(Path(f.frame_path)) for f in key_frames if f.frame_path and Path(f.frame_path).exists()]
        
        if not frame_paths:
            self.logger.error("No valid frame paths found")
            return self._create_empty_timeline(key_frames)
        
        self.logger.info(f"Prepared {len(frame_paths)} frames for analysis")
        
        # Create comprehensive prompt
        if progress_callback:
            progress_callback("Creating analysis prompt...")
        prompt = self._create_comprehensive_prompt(key_frames, test_steps, ocr_data)
        
        # Single API call with all key frames
        try:
            self.logger.info("Making comprehensive vision API call...")
            if progress_callback:
                progress_callback("Preparing frames for AI analysis...")
            
            if progress_callback:
                progress_callback(f"Analyzing {len(frame_paths)} video frames with AI...")
            
            with self.timed_operation("Comprehensive Vision Analysis"):
                # Use modular LLM provider
                response_text = self.generate_llm_response(prompt=prompt, image_paths=frame_paths)
            
            # Parse response into timeline
            if progress_callback:
                progress_callback("Parsing AI response into timeline...")
                
            timeline = self._parse_timeline_response(
                response_text,
                key_frames,
                ocr_data
            )
            
            if progress_callback:
                progress_callback("Timeline analysis complete")
            
            self.logger.info(
                f"✅ Timeline created: {len(timeline.events)} events, "
                f"{len(timeline.key_observations)} observations"
            )
            self.logger.debug(f"Narrative: {timeline.narrative[:200]}...")
            
            return timeline
            
        except Exception as e:
            self.logger.error(f"Comprehensive analysis failed: {e}", exc_info=True)
            return self._create_empty_timeline(key_frames)
    
    def _create_comprehensive_prompt(
        self,
        key_frames: List[VideoFrame],
        test_steps: List[TestStep],
        ocr_data: Dict[int, List[str]]
    ) -> str:
        """Create detailed prompt for comprehensive analysis."""
        
        # Format frame timestamps for context
        frame_timestamps = [f"{f.timestamp:.1f}s" for f in key_frames]
        
        # Include OCR context
        ocr_summary = self._summarize_ocr_data(ocr_data, key_frames)
        
        # Include test context
        steps_summary = "\n".join([
            f"Step {i+1}: {step.description}"
            for i, step in enumerate(test_steps)
        ])
        
        prompt = f"""You are analyzing a UI test video to create a COMPREHENSIVE TIMELINE of all events.

**Video Information:**
- Frames analyzed: {len(key_frames)} key frames
- Timestamps: {frame_timestamps[0]} through {frame_timestamps[-1]}
- Total duration: {key_frames[-1].timestamp:.1f} seconds

**Test Steps (Expected Sequence):**
{steps_summary}

**OCR Text Detected:**
{ocr_summary}

**Your Task:**
Analyze the frames chronologically and describe EVERYTHING you observe. Create a detailed timeline of ALL events.

For each significant event, note:
1. **Navigation & Page Loads**: URLs, page changes, redirects
2. **User Interactions**: Clicks, typing in inputs, selecting options
3. **UI State Changes**: Modals, dropdowns, filters, tooltips appearing/disappearing
4. **Content Updates**: Search results, product listings, dynamic text
5. **Visual Elements**: Buttons, inputs, navigation menus, icons visible at each stage
6. **Text Content**: Any readable text (combine with OCR data)
7. **Assertions/Validations**: Filter selections, result counts, validation messages

**CRITICAL - Negative Observations:**
When analyzing, you MUST explicitly note when UI elements are:
- MISSING (expected in test but not found in video)
- PRESENT (found as expected)
- DIFFERENT (found but in unexpected state)

For filter/option selections and assertions:
- List ALL available options you can actually see in each frame
- Explicitly state if expected options are NOT visible or NOT available
- Note checkbox/selection states (checked/unchecked, selected/unselected)
- Be ACCURATE - do NOT assume elements exist if you cannot see them
- Use EXACT phrases: "X is NOT visible", "X is NOT available", "X does NOT appear"

**MANDATORY NEGATIVE REPORTING:**
If a test step mentions an element (button, filter, option, text) but you CANNOT see it:
- You MUST explicitly state: "[Element Name] is NOT visible" or "[Element Name] is NOT available"
- Do NOT skip or ignore missing elements
- This is critical for detecting test failures

Example of GOOD analysis:
✓ "Neck filter section shows available options: 'Crew Neck', 'V-Neck'. IMPORTANT: 'Turtle Neck' option is NOT visible in the available filters."
✓ "Search results show 2 items for 'Rainbow sweater'. No filters are currently applied."
✓ "Filter dropdown expanded. Available options: 'Crew Neck' (unchecked), 'V-Neck' (unchecked). NOTE: 'Turtle Neck' is NOT available as an option."

Example of BAD analysis (AVOID):
✗ "Turtle Neck filter is applied" (when you cannot see this option exists)
✗ "Filter section visible" (too vague - list actual available options)
✗ Omitting mention of missing elements entirely

**Output Format (JSON):**
```json
{{
    "narrative": "Brief overall summary of what the test accomplishes",
    "key_observations": [
        "Important observation 1",
        "Important observation 2",
        ...
    ],
    "events": [
        {{
            "timestamp": 0.0,
            "frame_number": 0,
            "event_type": "navigation",
            "description": "Detailed description of what's happening",
            "ui_elements": ["search icon", "navigation bar", "logo"],
            "text_visible": ["Wrangler", "Sign In"],
            "confidence": 0.95
        }},
        {{
            "timestamp": 10.5,
            "frame_number": 10,
            "event_type": "click",
            "description": "User clicked the search icon to activate search bar",
            "ui_elements": ["search bar expanded", "search input field", "close icon"],
            "text_visible": ["Start typing to search"],
            "confidence": 1.0
        }},
        ...
    ]
}}
```

**Event Types:**
- `navigation`: Page loads, URL changes
- `click`: Button/link clicks, UI interactions
- `type`: Text input, form filling
- `ui_change`: Modals, dropdowns, filters, visual state changes
- `assertion`: Validation checks, filter states, result verification

**Important:**
- Be thorough - capture ALL observable changes
- Include timestamps from the frames
- Note UI elements visible at each stage
- Combine visual analysis with OCR text
- Provide high confidence (0.9-1.0) for clear observations
- This timeline will be used to verify all test steps, so completeness is critical

Analyze now and provide the comprehensive timeline."""

        return prompt
    
    def _summarize_ocr_data(
        self,
        ocr_data: Dict[int, List[str]],
        key_frames: List[VideoFrame]
    ) -> str:
        """Summarize OCR findings for prompt."""
        if not ocr_data:
            return "No OCR text detected"
        
        summary_lines = []
        for frame in key_frames[:10]:  # First 10 key frames
            texts = ocr_data.get(frame.frame_number, [])
            if texts:
                summary_lines.append(
                    f"Frame {frame.frame_number} ({frame.timestamp:.1f}s): {', '.join(texts[:8])}"
                )
        
        if not summary_lines:
            return "No significant text detected in key frames"
        
        return "\n".join(summary_lines)
    
    def _parse_timeline_response(
        self,
        response_text: str,
        key_frames: List[VideoFrame],
        ocr_data: Dict[int, List[str]]
    ) -> VideoTimeline:
        """Parse LLM response into VideoTimeline with robust error recovery."""
        try:
            # Extract JSON from response
            cleaned_text = response_text.strip()
            
            # Handle markdown code blocks
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[1].split("```")[0].strip()
            
            # Additional cleanup for potential prefixes/suffixes
            if not cleaned_text.startswith("{") and "{" in cleaned_text:
                cleaned_text = cleaned_text[cleaned_text.find("{"):]
            if not cleaned_text.endswith("}") and "}" in cleaned_text:
                cleaned_text = cleaned_text[:cleaned_text.rfind("}")+1]
            
            # Try parsing JSON, with repair attempts on failure
            data = self._try_parse_json_with_repair(cleaned_text)
            
            if data is None:
                self.logger.error("All JSON parsing attempts failed")
                self.logger.debug(f"Response text (first 1000 chars): {response_text[:1000]}...")
                return self._create_empty_timeline(key_frames)
            
            # Create timeline events
            events = []
            for event_data in data.get("events", []):
                try:
                    events.append(TimelineEvent(**event_data))
                except Exception as e:
                    self.logger.warning(f"Failed to parse event: {e}")
                    continue
            
            # Calculate total duration
            total_duration = key_frames[-1].timestamp if key_frames else 0
            
            timeline = VideoTimeline(
                total_duration=total_duration,
                total_frames_analyzed=len(key_frames),
                events=events,
                narrative=data.get("narrative", ""),
                key_observations=data.get("key_observations", [])
            )
            
            self.logger.info(f"Successfully parsed {len(events)} events from response")
            return timeline
            
        except Exception as e:
            self.logger.error(f"Failed to parse timeline response: {e}", exc_info=True)
            return self._create_empty_timeline(key_frames)
    
    def _try_parse_json_with_repair(self, json_text: str) -> Optional[Dict[str, Any]]:
        """
        Try to parse JSON with multiple repair strategies.
        
        Strategies:
        1. Direct parsing
        2. Fix common syntax errors (trailing commas, missing commas)
        3. Extract and parse individual components
        
        Returns:
            Parsed dict or None if all attempts fail
        """
        # Strategy 1: Direct parsing
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            self.logger.warning(f"Direct JSON parse failed: {e}")
        
        # Strategy 2: Fix common JSON syntax errors
        repaired_text = self._repair_json_syntax(json_text)
        try:
            return json.loads(repaired_text)
        except json.JSONDecodeError as e:
            self.logger.warning(f"Repaired JSON parse failed: {e}")
        
        # Strategy 3: Try to extract events array separately and build partial result
        try:
            partial_result = self._extract_partial_json(json_text)
            if partial_result and (partial_result.get("events") or partial_result.get("narrative")):
                self.logger.info("Recovered partial JSON data")
                return partial_result
        except Exception as e:
            self.logger.warning(f"Partial JSON extraction failed: {e}")
        
        # Strategy 4: Try truncating at the last valid JSON structure
        try:
            truncated = self._truncate_to_valid_json(json_text)
            if truncated:
                return json.loads(truncated)
        except Exception as e:
            self.logger.warning(f"Truncated JSON parse failed: {e}")
        
        return None
    
    def _repair_json_syntax(self, json_text: str) -> str:
        """
        Attempt to repair common JSON syntax errors.
        
        Fixes:
        - Trailing commas before ] or }
        - Missing commas between elements
        - Unescaped quotes in strings
        - Truncated strings at end
        """
        repaired = json_text
        
        # Fix trailing commas: ,] -> ] and ,} -> }
        repaired = re.sub(r',\s*]', ']', repaired)
        repaired = re.sub(r',\s*}', '}', repaired)
        
        # Fix missing commas between objects: }{ -> },{
        repaired = re.sub(r'}\s*{', '},{', repaired)
        
        # Fix missing commas between array elements: ]\s*[ -> ],[
        repaired = re.sub(r']\s*\[', '],[', repaired)
        
        # Fix missing commas after string values: "value"\s*" -> "value","
        repaired = re.sub(r'"\s*\n\s*"', '",\n"', repaired)
        
        # Fix missing commas after numbers: digits\s*" -> digits,"
        repaired = re.sub(r'(\d)\s*\n\s*"', r'\1,\n"', repaired)
        
        # Fix missing commas after true/false/null
        repaired = re.sub(r'(true|false|null)\s*\n\s*"', r'\1,\n"', repaired)
        
        # Ensure proper closing if truncated
        open_braces = repaired.count('{') - repaired.count('}')
        open_brackets = repaired.count('[') - repaired.count(']')
        
        # If we have unclosed structures, try to close them
        if open_braces > 0 or open_brackets > 0:
            # Remove potentially incomplete last element
            # Find the last complete element
            last_complete = max(
                repaired.rfind('},'),
                repaired.rfind('"],'),
                repaired.rfind('"}'),
                repaired.rfind('"]'),
            )
            if last_complete > len(repaired) // 2:
                repaired = repaired[:last_complete + 2]
                # Re-count and close
                open_braces = repaired.count('{') - repaired.count('}')
                open_brackets = repaired.count('[') - repaired.count(']')
            
            # Close unclosed brackets first, then braces
            repaired += ']' * open_brackets
            repaired += '}' * open_braces
        
        return repaired
    
    def _extract_partial_json(self, json_text: str) -> Optional[Dict[str, Any]]:
        """
        Extract what we can from partially valid JSON.
        
        Tries to extract:
        - narrative field
        - key_observations array
        - events array (as many as possible)
        """
        result = {
            "narrative": "",
            "key_observations": [],
            "events": []
        }
        
        # Extract narrative
        narrative_match = re.search(r'"narrative"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', json_text)
        if narrative_match:
            result["narrative"] = narrative_match.group(1).replace('\\"', '"')
        
        # Extract key_observations - find the array content
        obs_match = re.search(r'"key_observations"\s*:\s*\[(.*?)\]', json_text, re.DOTALL)
        if obs_match:
            obs_content = obs_match.group(1)
            # Extract individual strings
            observations = re.findall(r'"([^"]*(?:\\.[^"]*)*)"', obs_content)
            result["key_observations"] = [o.replace('\\"', '"') for o in observations]
        
        # Extract events - this is more complex, extract individual event objects
        events_match = re.search(r'"events"\s*:\s*\[(.*)', json_text, re.DOTALL)
        if events_match:
            events_content = events_match.group(1)
            # Find complete event objects using balanced brace matching
            events = self._extract_json_objects(events_content)
            for event_str in events:
                try:
                    event_data = json.loads(event_str)
                    result["events"].append(event_data)
                except:
                    continue
        
        return result if (result["events"] or result["narrative"]) else None
    
    def _extract_json_objects(self, text: str) -> List[str]:
        """Extract complete JSON objects from text using brace matching."""
        objects = []
        depth = 0
        start = -1
        
        for i, char in enumerate(text):
            if char == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and start >= 0:
                    obj_str = text[start:i+1]
                    objects.append(obj_str)
                    start = -1
        
        return objects
    
    def _truncate_to_valid_json(self, json_text: str) -> Optional[str]:
        """
        Try to find a valid JSON by progressively truncating.
        
        This handles cases where the LLM response was cut off mid-JSON.
        """
        # Try to find the last complete event in the events array
        # Look for patterns like: }, followed by ] to close events array
        
        # First, find where events array starts
        events_start = json_text.find('"events"')
        if events_start < 0:
            return None
        
        # Find complete event objects
        events_array_start = json_text.find('[', events_start)
        if events_array_start < 0:
            return None
        
        # Find all potential end points (complete events)
        potential_ends = []
        depth = 0
        in_events = False
        
        for i, char in enumerate(json_text[events_array_start:], events_array_start):
            if char == '[' and not in_events:
                in_events = True
                depth = 1
            elif char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 1:  # Just closed an event object
                    potential_ends.append(i)
            elif char == ']' and depth == 1:
                # Found the end of events array
                break
        
        # Try truncating at each potential end point, from last to first
        for end_pos in reversed(potential_ends):
            try:
                # Build truncated JSON: keep everything up to this event, close arrays/objects
                truncated = json_text[:end_pos + 1]
                
                # Count unclosed structures
                open_brackets = truncated.count('[') - truncated.count(']')
                open_braces = truncated.count('{') - truncated.count('}')
                
                # Close them
                truncated += ']' * open_brackets
                truncated += '}' * open_braces
                
                # Verify it parses
                result = json.loads(truncated)
                if result.get("events"):
                    self.logger.info(f"Successfully truncated JSON at position {end_pos}, recovered {len(result.get('events', []))} events")
                    return truncated
            except:
                continue
        
        return None
    
    def _create_empty_timeline(self, key_frames: List[VideoFrame]) -> VideoTimeline:
        """Create empty timeline on parsing failure."""
        return VideoTimeline(
            total_duration=key_frames[-1].timestamp if key_frames else 0,
            total_frames_analyzed=len(key_frames),
            events=[],
            narrative="Error: Failed to analyze video",
            key_observations=["Analysis failed - check logs for details"]
        )
    
    def verify_step_against_timeline(
        self,
        step: TestStep,
        timeline: VideoTimeline,
        ocr_data: Dict[int, List[str]],
        previous_step_timestamp: Optional[float] = None
    ) -> StepEvidence:
        """
        Gather evidence for a test step from the pre-analyzed timeline.
        NO ADDITIONAL API CALLS - uses timeline data only.
        
        Note: This method gathers EVIDENCE only. The actual pass/fail
        determination is done by VerificationAgent using LLM-based
        semantic analysis for better accuracy.
        
        Args:
            step: Test step to gather evidence for
            timeline: Comprehensive video timeline
            ocr_data: OCR results for additional text matching
            previous_step_timestamp: Timestamp of previous step (for temporal ordering)
            
        Returns:
            StepEvidence with gathered evidence for VerificationAgent
        """
        self.logger.debug(f"Gathering evidence for step {step.step_number}: {step.description}")
        
        # Extract keywords from step
        keywords = self._extract_keywords(step.description, step.action)
        self.logger.debug(f"Keywords: {keywords[:5]}...")
        
        # Calculate minimum timestamp for temporal ordering
        min_timestamp = max(0.0, (previous_step_timestamp or 0.0) + 0.5)
        
        # Find matching events in timeline with temporal constraint
        matching_events = timeline.find_events_matching(
            keywords=keywords,
            min_timestamp=min_timestamp,
            require_multiple_matches=True
        )
        
        # If no matches with strict requirements, try relaxed search
        if not matching_events:
            self.logger.debug("No matches with strict criteria, trying relaxed search...")
            matching_events = timeline.find_events_matching(
                keywords=keywords,
                min_timestamp=min_timestamp,
                require_multiple_matches=False
            )
        
        if not matching_events:
            self.logger.warning(
                f"No matching events found for step {step.step_number} "
                f"after timestamp {min_timestamp:.1f}s"
            )
            return StepEvidence(
                found=False,
                confidence=0.0,
                matching_events=[],
                description="No matching events found in timeline",
                reasoning=(
                    f"Searched for keywords: {', '.join(keywords[:5])} "
                    f"after timestamp {min_timestamp:.1f}s - no matches"
                )
            )
        
        # Get best match
        best_match = matching_events[0]
        
        # Calculate initial confidence based on keyword matching
        # Note: This is preliminary - VerificationAgent may adjust based on semantic analysis
        desc_lower = best_match.description.lower()
        text_lower = ' '.join(best_match.text_visible).lower()
        ui_lower = ' '.join(best_match.ui_elements).lower()
        combined = f"{desc_lower} {text_lower} {ui_lower}"
        
        matched_keywords = sum(1 for kw in keywords if kw.lower() in combined)
        keyword_ratio = matched_keywords / max(len(keywords), 1)
        
        # Base confidence from event + keyword matching
        base_confidence = best_match.confidence
        if keyword_ratio >= 0.7:
            base_confidence = min(1.0, base_confidence + 0.15)
        elif keyword_ratio >= 0.5:
            base_confidence = min(1.0, base_confidence + 0.10)
        elif keyword_ratio >= 0.3:
            base_confidence = min(1.0, base_confidence + 0.05)
        
        # Temporal ordering bonus
        if previous_step_timestamp and best_match.timestamp >= previous_step_timestamp:
            base_confidence = min(1.0, base_confidence + 0.05)
        
        # Weak match penalty
        if len(matching_events) == 1 and keyword_ratio < 0.4:
            base_confidence = max(0.5, base_confidence - 0.2)
        
        # Build evidence summary
        evidence_summary = self._build_detailed_evidence(matching_events[:3], keywords)
        
        self.logger.info(
            f"✓ Step {step.step_number}: Found {len(matching_events)} matches, "
            f"best at {best_match.timestamp:.1f}s (initial confidence: {base_confidence:.2f})"
        )
        
        return StepEvidence(
            found=True,
            confidence=base_confidence,
            timestamp=best_match.timestamp,
            frame_number=best_match.frame_number,
            matching_events=matching_events,
            description=best_match.description,
            reasoning=(
                f"Found {len(matching_events)} matching events. "
                f"Best match at {best_match.timestamp:.1f}s with {matched_keywords}/{len(keywords)} "
                f"keyword matches. Evidence: {evidence_summary}"
            )
        )
    
    def _extract_keywords(self, description: str, action: str) -> List[str]:
        """Extract keywords from step description and action."""
        text = f"{description} {action}".lower()
        
        # Extract quoted strings (high priority keywords)
        quoted = re.findall(r'"([^"]*)"', text)
        quoted = [q.strip() for q in quoted if len(q.strip()) > 2]
        
        # Extract regular words (filter stop words)
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been',
            'that', 'this', 'it', 'as', 'by', 'from', 'should', 'will'
        }
        words = re.findall(r'\b\w+\b', text)
        words = [w for w in words if len(w) > 2 and w not in stop_words]
        
        # Combine with quoted strings prioritized
        keywords = quoted + [w for w in words if w not in quoted]
        
        return keywords[:15]
    
    def _build_detailed_evidence(
        self,
        events: List[TimelineEvent],
        keywords: List[str]
    ) -> str:
        """
        Build detailed evidence string from multiple events.
        
        Provides rich context for verification reasoning.
        """
        if not events:
            return "No events found"
        
        evidence_parts = []
        for i, event in enumerate(events[:3], 1):  # Top 3 events
            matched_kw = [kw for kw in keywords if kw.lower() in event.description.lower()]
            evidence_parts.append(
                f"[{i}] {event.timestamp:.1f}s: {event.description[:100]}... "
                f"(matched: {', '.join(matched_kw[:3])})"
            )
        
        return " | ".join(evidence_parts)