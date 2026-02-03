"""Report generation utilities for multiple formats."""

import json
from datetime import datetime
from pathlib import Path

from analysis_agent.core.models import DeviationReport


class ReportGenerator:
    """Generates reports in multiple formats."""
    
    # Status colors: observed=green, uncertain=yellow, deviation=red
    STATUS_COLORS = {
        "observed": "#38ef7d",   # Green
        "uncertain": "#ffd93d",  # Yellow
        "deviation": "#f45c43",  # Red
    }
    
    STATUS_BG_COLORS = {
        "observed": "rgba(56, 239, 125, 0.15)",
        "uncertain": "rgba(255, 217, 61, 0.15)",
        "deviation": "rgba(244, 92, 67, 0.15)",
    }
    
    OVERALL_STATUS_COLORS = {
        "PASSED": "#38ef7d",    # Green
        "FAILED": "#f45c43",    # Red
        "UNCERTAIN": "#ffd93d"  # Yellow
    }
    
    @staticmethod
    def get_status_emoji(status: str, for_detail: bool = False) -> str:
        """Get emoji for status.
        
        Args:
            status: The status string (observed, deviation, uncertain)
            for_detail: If True, use caution emoji only for issues
        """
        status_lower = status.lower()
        if for_detail:
            # For detailed view - caution only for issues
            return {
                "observed": "✅",
                "deviation": "⚠️",
                "uncertain": "⚠️"
            }.get(status_lower, "❓")
        else:
            # For table/summary display
            return {
                "observed": "✅",
                "deviation": "❌",
                "uncertain": "⚠️"
            }.get(status_lower, "❓")
    
    @staticmethod
    def generate_json(report: DeviationReport) -> str:
        """Generate JSON report."""
        data = report.model_dump(mode='json')
        return json.dumps(data, indent=2, default=str)
    
    @staticmethod
    def generate_markdown(report: DeviationReport) -> str:
        """Generate Markdown report."""
        md = f"""# Test Deviation Report: {report.test_name}

## Executive Summary

- **Overall Status**: {report.overall_status}
- **Execution Date**: {report.execution_date.strftime('%Y-%m-%d %H:%M:%S')}
- **Total Steps**: {report.total_steps}
- **Observed Steps**: {report.observed_steps} ✅ (Green)
- **Deviated Steps**: {report.deviated_steps} ❌ (Red)
- **Uncertain Steps**: {report.uncertain_steps} ⚠️ (Yellow)
- **Pass Rate**: {report.pass_rate:.1f}%

{report.summary}

## Strategy Used

- **Frame Interval**: {report.strategy_used.frame_interval}s
- **Max Frames**: {report.strategy_used.max_frames}
- **Confidence Threshold**: {report.strategy_used.confidence_threshold}
- **Priority Mode**: {report.strategy_used.priority_mode}

**Reasoning**: {report.strategy_used.reasoning}

## Verification Results

| # | Step | Status | Confidence | Evidence |
|---|------|--------|------------|----------|
"""
        
        for result in report.verification_results:
            status_emoji = ReportGenerator.get_status_emoji(result.status.value)
            
            md += f"| {result.step.step_number} | {result.step.description} | {status_emoji} {result.status.value} | {result.confidence:.0%} | {result.evidence} |\n"
        
        md += "\n## Detailed Step Analysis\n\n"
        
        for result in report.verification_results:
            # Use caution emoji only for issues, green check for observed
            detail_emoji = ReportGenerator.get_status_emoji(result.status.value, for_detail=True)
            md += f"### {detail_emoji} Step {result.step.step_number}: {result.step.description}\n\n"
            md += f"- **Action**: {result.step.action}\n"
            md += f"- **Status**: {result.status.value.upper()}\n"
            md += f"- **Confidence**: {result.confidence:.1%}\n"
            
            if result.video_timestamp is not None:
                md += f"- **Video Timestamp**: {result.video_timestamp:.2f}s\n"
            
            md += f"\n**Evidence**: {result.evidence}\n\n"
            
            if result.ocr_detected_text:
                md += f"**OCR Matches**: {', '.join(result.ocr_detected_text)}\n\n"
            
            if result.vision_analysis:
                md += f"**Vision Analysis**: {result.vision_analysis}\n\n"
            
            if result.agent_decisions:
                md += f"**Agent Decisions**:\n"
                for decision in result.agent_decisions:
                    md += f"- {decision.agent_name}: {decision.decision} (confidence: {decision.confidence:.1%})\n"
                md += "\n"
            
            md += "---\n\n"
        
        return md
    
    @staticmethod
    def generate_html(report: DeviationReport) -> str:
        """Generate well-styled HTML report with proper status colors."""
        
        overall_color = ReportGenerator.OVERALL_STATUS_COLORS.get(report.overall_status, "#6c757d")
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Deviation Report - {report.test_name}</title>
    <style>
        :root {{
            --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --success-gradient: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            --warning-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            --danger-gradient: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
            
            --observed-color: #38ef7d;
            --uncertain-color: #ffd93d;
            --deviation-color: #f45c43;
            
            --bg-dark: #0e1117;
            --bg-card: #1a1f2e;
            --bg-hover: #252b3b;
            --text-primary: #ffffff;
            --text-secondary: #a0aec0;
            --border-color: #2d3748;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background: linear-gradient(180deg, #0e1117 0%, #1a1f2e 100%);
            min-height: 100vh;
            padding: 2rem;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        /* Header Section */
        .header {{
            background: var(--primary-gradient);
            padding: 2.5rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2), 0 0 20px rgba(102, 126, 234, 0.3);
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            animation: shimmer 3s infinite linear;
        }}
        
        @keyframes shimmer {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .header h1 {{
            color: white;
            font-size: 2.5rem;
            font-weight: 700;
            margin: 0 0 0.5rem 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            position: relative;
            z-index: 1;
        }}
        
        .header .subtitle {{
            color: rgba(255,255,255,0.9);
            font-size: 1.1rem;
            position: relative;
            z-index: 1;
        }}
        
        .header .meta {{
            color: rgba(255,255,255,0.8);
            font-size: 0.9rem;
            margin-top: 1rem;
            position: relative;
            z-index: 1;
        }}
        
        /* Overall Status Banner */
        .status-banner {{
            background: {overall_color};
            padding: 1.5rem 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }}
        
        .status-banner h2 {{
            color: white;
            font-size: 1.8rem;
            margin: 0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
        }}
        
        .status-banner .summary-text {{
            color: rgba(255,255,255,0.9);
            font-size: 0.95rem;
            margin-top: 0.5rem;
        }}
        
        /* Metrics Cards */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .metric-card {{
            background: var(--bg-card);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            border: 1px solid var(--border-color);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
        }}
        
        .metric-card.total {{ border-top: 4px solid #667eea; }}
        .metric-card.observed {{ border-top: 4px solid var(--observed-color); }}
        .metric-card.deviation {{ border-top: 4px solid var(--deviation-color); }}
        .metric-card.uncertain {{ border-top: 4px solid var(--uncertain-color); }}
        
        .metric-value {{
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}
        
        .metric-value.total {{
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .metric-value.observed {{ color: var(--observed-color); }}
        .metric-value.deviation {{ color: var(--deviation-color); }}
        .metric-value.uncertain {{ color: var(--uncertain-color); }}
        
        .metric-label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        /* Section Headers */
        .section-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin: 2rem 0 1.5rem 0;
        }}
        
        .section-header h2 {{
            color: var(--text-primary);
            font-size: 1.5rem;
            font-weight: 600;
            margin: 0;
        }}
        
        .section-header .icon {{
            font-size: 1.5rem;
        }}
        
        /* Executive Summary Section */
        .summary-section {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            border: 1px solid var(--border-color);
        }}
        
        .summary-section p {{
            color: var(--text-secondary);
            line-height: 1.8;
        }}
        
        /* Results Table */
        .results-table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            background: var(--bg-card);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            margin-bottom: 2rem;
        }}
        
        .results-table th {{
            background: var(--bg-dark);
            color: var(--text-primary);
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 1px;
        }}
        
        .results-table td {{
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-primary);
        }}
        
        .results-table tr:last-child td {{
            border-bottom: none;
        }}
        
        .results-table tr:hover td {{
            background: var(--bg-hover);
        }}
        
        .results-table .action-code {{
            font-family: 'SF Mono', Monaco, 'Courier New', monospace;
            font-size: 0.85rem;
            color: var(--text-secondary);
            background: rgba(102, 126, 234, 0.1);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
        }}
        
        /* Status Badges */
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.4rem 0.8rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        
        .status-badge.observed {{
            background: rgba(56, 239, 125, 0.2);
            color: var(--observed-color);
        }}
        .status-badge.deviation {{
            background: rgba(244, 92, 67, 0.2);
            color: var(--deviation-color);
        }}
        .status-badge.uncertain {{
            background: rgba(255, 217, 61, 0.2);
            color: var(--uncertain-color);
        }}
        
        /* Confidence Bar */
        .confidence-bar {{
            width: 100px;
            height: 8px;
            background: var(--bg-dark);
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 0.25rem;
        }}
        
        .confidence-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }}
        
        .confidence-fill.high {{ background: var(--success-gradient); }}
        .confidence-fill.medium {{ background: linear-gradient(90deg, #ffd93d, #f093fb); }}
        .confidence-fill.low {{ background: var(--danger-gradient); }}
        
        .confidence-text {{
            font-size: 0.8rem;
            color: var(--text-secondary);
        }}
        
        /* Detailed Steps Section */
        .step-detail {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border: 1px solid var(--border-color);
            border-left: 4px solid var(--border-color);
        }}
        
        .step-detail.observed {{ border-left-color: var(--observed-color); }}
        .step-detail.deviation {{ border-left-color: var(--deviation-color); }}
        .step-detail.uncertain {{ border-left-color: var(--uncertain-color); }}
        
        .step-detail h3 {{
            color: var(--text-primary);
            font-size: 1.1rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .step-detail .detail-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }}
        
        .step-detail .detail-item {{
            padding: 0.75rem;
            background: var(--bg-dark);
            border-radius: 8px;
        }}
        
        .step-detail .detail-label {{
            color: var(--text-secondary);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.25rem;
        }}
        
        .step-detail .detail-value {{
            color: var(--text-primary);
            font-size: 0.95rem;
        }}
        
        .evidence-box {{
            background: var(--bg-dark);
            border-radius: 8px;
            padding: 1rem;
            margin-top: 1rem;
            border-left: 3px solid var(--primary-color);
        }}
        
        .evidence-box.success {{ border-left-color: var(--observed-color); }}
        .evidence-box.warning {{ border-left-color: var(--uncertain-color); }}
        .evidence-box.error {{ border-left-color: var(--deviation-color); }}
        
        .evidence-box p {{
            color: var(--text-secondary);
            font-size: 0.95rem;
            line-height: 1.6;
        }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }}
        
        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}
        
        /* Print Styles */
        @media print {{
            body {{
                background: white;
                color: #333;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🎬 TestZeus Analysis Report</h1>
            <div class="subtitle">{report.test_name}</div>
            <div class="meta">Generated: {report.execution_date.strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <!-- Overall Status Banner -->
        <div class="status-banner">
            <div>
                <h2>{report.overall_status}</h2>
                <div class="summary-text">{report.summary}</div>
            </div>
        </div>
        
        <!-- Metrics Grid -->
        <div class="metrics-grid">
            <div class="metric-card total">
                <div class="metric-value total">{report.total_steps}</div>
                <div class="metric-label">Total Steps</div>
            </div>
            <div class="metric-card observed">
                <div class="metric-value observed">{report.observed_steps}</div>
                <div class="metric-label">✅ Observed (Green)</div>
            </div>
            <div class="metric-card deviation">
                <div class="metric-value deviation">{report.deviated_steps}</div>
                <div class="metric-label">❌ Deviated (Red)</div>
            </div>
            <div class="metric-card uncertain">
                <div class="metric-value uncertain">{report.uncertain_steps}</div>
                <div class="metric-label">⚠️ Uncertain (Yellow)</div>
            </div>
            <div class="metric-card total">
                <div class="metric-value total">{report.pass_rate:.1f}%</div>
                <div class="metric-label">Pass Rate</div>
            </div>
        </div>
        
        <!-- Verification Results Table -->
        <div class="section-header">
            <span class="icon">📋</span>
            <h2>Verification Results</h2>
        </div>
        
        <table class="results-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Step Description</th>
                    <th>Status</th>
                    <th>Confidence</th>
                    <th>Evidence</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for result in report.verification_results:
            status_val = result.status.value.lower()
            status_emoji = ReportGenerator.get_status_emoji(result.status.value)
            confidence_pct = int(result.confidence * 100)
            
            # Determine confidence class
            if result.confidence >= 0.85:
                conf_class = "high"
            elif result.confidence >= 0.5:
                conf_class = "medium"
            else:
                conf_class = "low"
            
            html += f"""
                <tr>
                    <td><strong>{result.step.step_number}</strong></td>
                    <td>
                        <strong>{result.step.description}</strong><br>
                        <span class="action-code">{result.step.action}</span>
                    </td>
                    <td><span class="status-badge {status_val}">{status_emoji} {result.status.value.upper()}</span></td>
                    <td>
                        <div class="confidence-bar">
                            <div class="confidence-fill {conf_class}" style="width: {confidence_pct}%"></div>
                        </div>
                        <span class="confidence-text">{confidence_pct}%</span>
                    </td>
                    <td>{result.evidence[:100]}{'...' if len(result.evidence) > 100 else ''}</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
        
        <!-- Detailed Step Analysis -->
        <div class="section-header">
            <span class="icon">🔍</span>
            <h2>Detailed Step Analysis</h2>
        </div>
"""
        
        for result in report.verification_results:
            status_val = result.status.value.lower()
            # Use caution emoji only for issues, green check for observed
            detail_emoji = ReportGenerator.get_status_emoji(result.status.value, for_detail=True)
            
            # Determine evidence box class
            if status_val == "observed":
                evidence_class = "success"
            elif status_val == "deviation":
                evidence_class = "error"
            else:
                evidence_class = "warning"
            
            html += f"""
        <div class="step-detail {status_val}">
            <h3>{detail_emoji} Step {result.step.step_number}: {result.step.description}</h3>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Action</div>
                    <div class="detail-value"><code>{result.step.action}</code></div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Status</div>
                    <div class="detail-value"><span class="status-badge {status_val}">{result.status.value.upper()}</span></div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Confidence</div>
                    <div class="detail-value">{result.confidence:.1%}</div>
                </div>
"""
            
            if result.video_timestamp is not None:
                html += f"""
                <div class="detail-item">
                    <div class="detail-label">Video Timestamp</div>
                    <div class="detail-value">⏱️ {result.video_timestamp:.2f}s</div>
                </div>
"""
            
            html += f"""
            </div>
            <div class="evidence-box {evidence_class}">
                <div class="detail-label">Evidence</div>
                <p>{result.evidence}</p>
            </div>
"""
            
            if result.vision_analysis:
                html += f"""
            <div class="evidence-box success">
                <div class="detail-label">Vision Analysis</div>
                <p>{result.vision_analysis}</p>
            </div>
"""
            
            html += """
        </div>
"""
        
        html += f"""
        <!-- Footer -->
        <div class="footer">
            <p>Generated by <strong>TestZeus Analysis Agent</strong> • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html