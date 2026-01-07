# diagnostics.py
"""
DIAGNOSTICS — Diagnostic output handler (disk-only)

Sprint 06.1 scope: Melt HIT/MISS diagnostic observability

Responsibilities:
- Reset diagnostic files on program start
- Write JSON diagnostics (./diagnostics/run_diagnostics.json)
- Write summary text (./diagnostics/run_diagnostics_summary.txt)
- Accumulate data across scan cycles within one run
- Overwrite files (not append) on each write

Contract: v1.2 Section 8
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict

DIAGNOSTICS_DIR = "./__diagnostics__"
JSON_FILE = os.path.join(DIAGNOSTICS_DIR, "run_diagnostics.json")
SUMMARY_FILE = os.path.join(DIAGNOSTICS_DIR, "run_diagnostics_summary.txt")


def reset_diagnostics():
    """
    Reset diagnostic files on program start.
    
    Creates diagnostics directory if not exists.
    Overwrites both files with empty/placeholder content.
    """
    # Create directory
    os.makedirs(DIAGNOSTICS_DIR, exist_ok=True)
    
    # Reset JSON file
    empty_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_listings_seen": 0,
        "eligible_count": 0,
        "hit_count": 0,
        "miss_count": 0,
        "ineligible_count": 0,
        "pros_count": 0,
        "rejection_buckets": {},
        "samples_by_reason": {}
    }
    
    with open(JSON_FILE, "w") as f:
        json.dump(empty_data, f, indent=2)
    
    # Reset summary file
    summary = """=== DIAGNOSTICS SUMMARY ===
Run: (awaiting data)

Total Listings Seen: 0
  Eligible: 0
  Ineligible: 0

Classification Results:
  HIT: 0
  MISS: 0
  PROS: 0

Top Rejection Reasons:
  (none)

===========================
"""
    
    with open(SUMMARY_FILE, "w") as f:
        f.write(summary)


def write_diagnostics(data: Dict[str, Any]):
    """
    Write diagnostic data to JSON and summary files.
    
    Overwrites both files with current data.
    Called after each scan cycle (or at least once per run).
    
    Args:
        data: Diagnostic data from classifier.get_diagnostics()
    """
    # Create directory if not exists
    os.makedirs(DIAGNOSTICS_DIR, exist_ok=True)
    
    # Add timestamp
    data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Write JSON file
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=2)
    
    # Write summary file
    summary = _build_summary(data)
    with open(SUMMARY_FILE, "w") as f:
        f.write(summary)


def _build_summary(data: Dict[str, Any]) -> str:
    """
    Build human-readable summary text.
    
    Args:
        data: Diagnostic data
    
    Returns:
        Formatted summary string
    """
    lines = []
    
    # Header
    lines.append("=== DIAGNOSTICS SUMMARY ===")
    lines.append(f"Run: {data.get('timestamp', 'unknown')}")
    lines.append("")
    
    # Counts
    total = data.get("total_listings_seen", 0)
    eligible = data.get("eligible_count", 0)
    ineligible = data.get("ineligible_count", 0)
    
    lines.append(f"Total Listings Seen: {total}")
    lines.append(f"  Eligible: {eligible}")
    lines.append(f"  Ineligible: {ineligible}")
    lines.append("")
    
    # Classification results
    hit_count = data.get("hit_count", 0)
    miss_count = data.get("miss_count", 0)
    pros_count = data.get("pros_count", 0)
    
    lines.append("Classification Results:")
    lines.append(f"  HIT: {hit_count}")
    lines.append(f"  MISS: {miss_count}")
    lines.append(f"  PROS: {pros_count}")
    lines.append("")
    
    # Top rejection reasons
    rejection_buckets = data.get("rejection_buckets", {})
    
    if rejection_buckets:
        # Sort by count (descending)
        sorted_reasons = sorted(
            rejection_buckets.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]  # Top 5
        
        lines.append("Top Rejection Reasons:")
        for i, (reason, count) in enumerate(sorted_reasons, 1):
            lines.append(f"  {i}. {reason}: {count}")
    else:
        lines.append("Top Rejection Reasons:")
        lines.append("  (none)")
    
    lines.append("")
    
    # Sample titles (only for top reason)
    samples_by_reason = data.get("samples_by_reason", {})
    
    if samples_by_reason and rejection_buckets:
        # Get top reason
        top_reason = sorted_reasons[0][0] if sorted_reasons else None
        
        if top_reason and top_reason in samples_by_reason:
            samples = samples_by_reason[top_reason]
            
            lines.append(f"Sample Titles ({top_reason}):")
            for sample in samples[:3]:  # Max 3
                title = sample.get("title", "Unknown")
                reason_detail = sample.get("reason_detail", "")
                lines.append(f'  - "{title}" ({reason_detail})')
            lines.append("")
    
    # Footer
    lines.append("===========================")
    
    return "\n".join(lines)


#EndOfFile
