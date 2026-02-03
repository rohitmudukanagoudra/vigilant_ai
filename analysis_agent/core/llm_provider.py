from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import os
import subprocess
from google import genai
from google.genai import types
from analysis_agent.core.config import Settings

class LLMBase(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(self, prompt: str, image_paths: Optional[List[str]] = None) -> str:
        """Generate text from prompt (and optional images)."""
        pass

class GeminiProvider(LLMBase):
    """Provider for Google's Gemini API."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.vision_model_name = "gemini-2.5-flash"  # Use flash for multi-modal
        
    def generate(self, prompt: str, image_paths: Optional[List[str]] = None) -> str:
        max_retries = 5
        base_delay = 5  # Start with 5 seconds for 429s
        
        for attempt in range(max_retries + 1):
            try:
                model_to_use = self.vision_model_name if image_paths else self.model_name
                if attempt > 0:
                    print(f"DEBUG: Retry attempt {attempt}/{max_retries} with model {model_to_use}")
                else:
                    print(f"DEBUG: Generating content with model {model_to_use}")
                
                contents = []
                
                if image_paths:
                    import PIL.Image
                    import io
                    for path in image_paths:
                        if os.path.exists(path):
                            img = PIL.Image.open(path)
                            # Convert image to bytes
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format=img.format or 'PNG')
                            img_bytes = img_byte_arr.getvalue()
                            contents.append(types.Part.from_bytes(data=img_bytes, mime_type=f"image/{(img.format or 'PNG').lower()}"))
                        else:
                            print(f"Warning: Image not found at {path}")
                
                contents.append(prompt)
                
                response = self.client.models.generate_content(
                    model=model_to_use,
                    contents=contents
                )
                
                # Check for empty response
                if not response.text:
                    print(f"DEBUG: Empty response received")
                    return "{}"  # Return empty JSON compatible string if blocked
                
                print(f"DEBUG: Response text prefix: {response.text[:100]}")
                return response.text
                
            except Exception as e:
                error_str = str(e)
                # Check for rate limit errors (429 or RESOURCE_EXHAUSTED)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff: 5, 10, 20, 40, 80
                        print(f"WARNING: Rate limit hit (429). Retrying in {delay}s...")
                        import time
                        time.sleep(delay)
                        continue
                    else:
                        print(f"ERROR: Max retries exhausted for rate limit.")
                
                # For other errors or if max retries reached
                print(f"ERROR in GeminiProvider: {e}")
                return f"Error generating content: {str(e)}"

class EncapsulatedCLIProvider(LLMBase):
    """Provider that wraps a CLI tool (e.g., Gemini CLI or custom wrapper)."""
    
    def __init__(self, command_prefix: List[str]):
        self.command_prefix = command_prefix
        
    def generate(self, prompt: str, image_paths: Optional[List[str]] = None) -> str:
        try:
            cmd = self.command_prefix.copy()
            
            if image_paths:
                for path in image_paths:
                    cmd.extend(["--image", path])
            
            cmd.extend([prompt])
            
            # Execute CLI
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=60
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"CLI Error: {result.stderr}")
                
            return result.stdout.strip()
            
        except Exception as e:
            return f"CLI Execution Failed: {str(e)}"

class OpenSourceProvider(LLMBase):
    """Placeholder for local Open Source models (e.g., via Ollama/HF)."""
    
    def __init__(self, endpoint: str = "http://localhost:11434"):
        self.endpoint = endpoint
        
    def generate(self, prompt: str, image_paths: Optional[List[str]] = None) -> str:
        # Implementation for Ollama or similar local API would go here
        # keeping it simple for now
        return "Open Source Provider not yet fully implemented."

class LLMFactory:
    """Factory to create LLM providers based on settings."""
    
    @staticmethod
    def create_provider(settings: Settings) -> LLMBase:
        provider_type = getattr(settings, "llm_provider", "gemini").lower()
        
        if provider_type == "gemini":
            return GeminiProvider(settings.gemini_api_key)
        elif provider_type == "cli":
            # Example: settings.cli_command = ["gemini", "query"]
            cmd = getattr(settings, "cli_command", ["echo"])
            return EncapsulatedCLIProvider(cmd)
        elif provider_type == "opensource":
            return OpenSourceProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {provider_type}")
