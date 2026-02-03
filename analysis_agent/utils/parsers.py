"""Input file parsers for planning logs and test outputs."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any

from analysis_agent.core.models import PlanningLog, TestOutput, TestStep


class PlanningLogParser:
    """Parser for agent planning logs (JSON format)."""
    
    @staticmethod
    def parse(content: bytes) -> PlanningLog:
        """Parse planning log from JSON content."""
        data = json.loads(content.decode('utf-8'))
        steps = []
        is_audit = False
        
        # Extract steps from planner_agent messages
        if 'planner_agent' in data:
            messages = data['planner_agent']
            step_number = 1
            
            # Use index-based loop to look ahead for outcomes (audit mode compatibility)
            for i in range(len(messages)):
                message = messages[i]
                
                if message.get('role') == 'assistant' and 'content' in message:
                    content_data = message['content']
                    
                    # Extract next_step and description
                    next_step = content_data.get('next_step', '')
                    summary = content_data.get('next_step_summary', '')
                    
                    if next_step:
                        # Check if next message is a user message (the agent's outcome)
                        outcome_text = None
                        if i + 1 < len(messages):
                            next_msg = messages[i+1]
                            if next_msg.get('role') == 'user':
                                outcome_text = next_msg.get('content', '')
                                is_audit = True # Found agent observations, trigger Audit Mode
                        
                        steps.append(TestStep(
                            step_number=step_number,
                            description=summary if summary else next_step,
                            action=next_step,
                            expected_outcome=outcome_text
                        ))
                        step_number += 1
        
        return PlanningLog(steps=steps, metadata={'is_audit_mode': is_audit, 'raw_data': data})




class TestOutputParser:
    """Parser for test output files (XML format)."""
    
    @staticmethod
    def parse(content: bytes) -> TestOutput:
        """Parse test output from XML content."""
        root = ET.fromstring(content.decode('utf-8'))
        
        # Find first testsuite
        testsuite = root.find('.//testsuite')
        if testsuite is None:
            raise ValueError("No testsuite found in XML")
        
        # Find first testcase
        testcase = testsuite.find('.//testcase')
        if testcase is None:
            raise ValueError("No testcase found in XML")
        
        test_name = testcase.get('name', 'Unknown Test')
        duration = float(testcase.get('time', 0))
        
        # Check for failure
        failure = testcase.find('failure')
        if failure is not None:
            status = 'FAILED'
            failure_message = failure.get('message', failure.text)
        else:
            status = 'PASSED'
            failure_message = None
        
        return TestOutput(
            test_name=test_name,
            status=status,
            duration=duration,
            failure_message=failure_message
        )