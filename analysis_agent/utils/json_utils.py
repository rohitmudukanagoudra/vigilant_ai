import json
import re
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("JSON_UTILS")

def clean_json_response(response_text: str) -> str:
    """Clean LLM response to extract JSON string."""
    if not response_text or not response_text.strip():
        return ""
    
    text = response_text.strip()
    
    # Remove markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    
    # Find JSON start/end (braces or brackets)
    # Prefer whichever comes first that has a matching closer
    brace_start = text.find("{")
    bracket_start = text.find("[")
    
    if brace_start >= 0 and (bracket_start < 0 or brace_start < bracket_start):
        start = brace_start
        end = text.rfind("}") + 1
    elif bracket_start >= 0:
        start = bracket_start
        end = text.rfind("]") + 1
    else:
        return text
    
    if start >= 0 and end > start:
        text = text[start:end]
        
    return text

def repair_json_syntax(json_text: str) -> str:
    """Attempt to repair common JSON syntax errors."""
    repaired = json_text
    
    # Fix trailing commas: ,] -> ] and ,} -> }
    repaired = re.sub(r',\s*]', ']', repaired)
    repaired = re.sub(r',\s*}', '}', repaired)
    
    # Fix missing commas between objects: }{ -> },{
    repaired = re.sub(r'}\s*{', '},{', repaired)
    
    # Fix missing commas between array elements: ] [ -> ],[
    repaired = re.sub(r']\s*\[', '],[', repaired)
    
    # Fix missing commas after values at end of line
    # "value"\s*\n\s*" -> "value",\n"
    repaired = re.sub(r'"\s*\n\s*"', '",\n"', repaired)
    repaired = re.sub(r'(\d)\s*\n\s*"', r'\1,\n"', repaired)
    repaired = re.sub(r'(true|false|null)\s*\n\s*"', r'\1,\n"', repaired)
    
    # Ensure proper closing if truncated
    open_braces = repaired.count('{') - repaired.count('}')
    open_brackets = repaired.count('[') - repaired.count(']')
    
    if open_braces > 0 or open_brackets > 0:
        # Close unclosed structures
        repaired += ']' * max(0, open_brackets)
        repaired += '}' * max(0, open_braces)
        
    return repaired

def _extract_json_objects(text: str) -> List[str]:
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

def extract_partial_json(json_text: str, fields: List[str]) -> Dict[str, Any]:
    """
    Extract specific fields from partially valid JSON.
    """
    result = {}
    for field in fields:
        # Simple regex for string fields
        match = re.search(f'"{field}"\\s*:\\s*"([^"]*(?:\\\\.[^"]*)*)"', json_text)
        if match:
            result[field] = match.group(1).replace('\\"', '"')
    
    # Try to extract arrays if requested
    if "events" in fields:
        events_match = re.search(r'"events"\s*:\s*\[(.*)', json_text, re.DOTALL)
        if events_match:
            events_content = events_match.group(1)
            objects = _extract_json_objects(events_content)
            result["events"] = []
            for obj_str in objects:
                try:
                    result["events"].append(json.loads(obj_str))
                except:
                    continue
                    
    return result

def truncate_to_valid_json(json_text: str) -> Optional[str]:
    """Try to find a valid JSON by progressively truncating from the end."""
    # Look for last complete object or array element
    for i in range(len(json_text) - 1, 0, -1):
        if json_text[i] in ['}', ']']:
            try:
                candidate = json_text[:i+1]
                # Close any remaining structures
                open_braces = candidate.count('{') - candidate.count('}')
                open_brackets = candidate.count('[') - candidate.count(']')
                if open_braces > 0: candidate += '}' * open_braces
                if open_brackets > 0: candidate += ']' * open_brackets
                
                return candidate
            except:
                continue
    return None

def try_parse_json(json_text: str) -> Optional[Any]:
    """Parse JSON with multiple repair strategies."""
    if not json_text:
        return None
        
    # Strategy 1: Direct parsing
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        pass
        
    # Strategy 2: Clean and try
    cleaned = clean_json_response(json_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
        
    # Strategy 3: Repair syntax and try
    repaired = repair_json_syntax(cleaned)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
        
    # Strategy 4: Truncate and try
    truncated = truncate_to_valid_json(cleaned)
    if truncated:
        try:
            return json.loads(truncated)
        except:
            pass
            
    return None
