"""OCR Agent - Text extraction and analysis."""

from typing import List
import easyocr

from analysis_agent.agents.base_agent import BaseAgent
from analysis_agent.core.models import VideoFrame
from analysis_agent.core.config import Settings


class OCRAgent(BaseAgent):
    """
    Agent that extracts and analyzes text from video frames.
    Works collaboratively with Vision Agent.
    """
    
    def __init__(self, settings: Settings):
        """Initialize OCR agent."""
        super().__init__("OCR")
        self.settings = settings
        languages = settings.ocr_languages.split(',')
        self.reader = easyocr.Reader(languages, gpu=False)
        self.logger.info(f"OCR initialized with languages: {languages}")
    
    def analyze_frames(self, frames: List[VideoFrame]) -> List[VideoFrame]:
        """
        Extract text from all frames.
        
        Args:
            frames: List of video frames
            
        Returns:
            Frames with ocr_text populated
        """
        self.logger.info(f"Analyzing {len(frames)} frames for text...")
        
        for i, frame in enumerate(frames):
            if frame.frame_path:
                try:
                    # Perform OCR
                    results = self.reader.readtext(
                        frame.frame_path,
                        detail=1
                    )
                    
                    # Extract text with confidence above threshold
                    frame.ocr_text = [
                        text for _, text, conf in results
                        if conf >= self.settings.ocr_confidence_threshold
                    ]
                    
                    if frame.ocr_text:
                        self.logger.debug(f"Frame {i}: Found {len(frame.ocr_text)} text elements")
                        
                except Exception as e:
                    self.logger.warning(f"OCR failed for frame {i}: {e}")
                    frame.ocr_text = []
        
        total_text_found = sum(1 for f in frames if f.ocr_text)
        self.logger.info(f"Found text in {total_text_found}/{len(frames)} frames")
        
        return frames
    
    def find_text_matches(
        self,
        frames: List[VideoFrame],
        keywords: List[str]
    ) -> List[VideoFrame]:
        """
        Find frames containing specific keywords.
        
        Args:
            frames: Video frames with OCR text
            keywords: Keywords to search for
            
        Returns:
            Frames containing any of the keywords
        """
        matching_frames = []
        
        for frame in frames:
            if frame.ocr_text:
                frame_text = ' '.join(frame.ocr_text).lower()
                if any(kw.lower() in frame_text for kw in keywords):
                    matching_frames.append(frame)
        
        return matching_frames