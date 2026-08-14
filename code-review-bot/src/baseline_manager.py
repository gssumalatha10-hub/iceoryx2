#!/usr/bin/env python3
"""
Baseline and Deduplication Manager
Tracks historical findings and filters only new issues
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Set, List, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BaselineFinding:
    """A baseline finding from prior analysis"""
    fingerprint: str
    rule_id: str
    file: str
    line: int
    tool: str
    first_seen: str
    last_seen: str
    status: str  # 'open', 'fixed', 'wont_fix', 'false_positive'
    justification: str = ""


class BaselineManager:
    """Manages baseline of existing findings to filter new issues"""
    
    def __init__(self, baseline_file: str = ".review-baseline.json"):
        """
        Args:
            baseline_file: Path to store baseline findings
        """
        self.baseline_file = Path(baseline_file)
        self.baseline: Dict[str, BaselineFinding] = {}
        self._load_baseline()
    
    def _load_baseline(self):
        """Load baseline from file"""
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file, 'r') as f:
                    data = json.load(f)
                    for fp, finding_dict in data.items():
                        self.baseline[fp] = BaselineFinding(**finding_dict)
                print(f"✓ Loaded baseline with {len(self.baseline)} known findings")
            except Exception as e:
                print(f"⚠ Failed to load baseline: {e}")
    
    def _save_baseline(self):
        """Save baseline to file"""
        data = {
            fp: {
                'fingerprint': f.fingerprint,
                'rule_id': f.rule_id,
                'file': f.file,
                'line': f.line,
                'tool': f.tool,
                'first_seen': f.first_seen,
                'last_seen': f.last_seen,
                'status': f.status,
                'justification': f.justification
            }
            for fp, f in self.baseline.items()
        }
        
        with open(self.baseline_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Saved baseline with {len(self.baseline)} findings")
    
    def compute_fingerprint(self, finding: Dict[str, Any]) -> str:
        """Compute stable fingerprint for a finding"""
        # Use rule, file, line, and message to create stable ID
        parts = [
            finding.get('rule_id', ''),
            finding.get('file', ''),
            str(finding.get('line', 0)),
            finding.get('message', '')[:50]
        ]
        
        fp_text = "|".join(parts)
        return hashlib.sha256(fp_text.encode()).hexdigest()[:16]
    
    def filter_new_findings(self, current_findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter findings to report only new ones.
        
        Returns:
            List of findings that are new or changed since baseline
        """
        new_findings = []
        now = datetime.now().isoformat()
        
        for finding in current_findings:
            fp = self.compute_fingerprint(finding)
            
            if fp not in self.baseline:
                # New finding
                finding['is_new'] = True
                new_findings.append(finding)
                
                # Add to baseline
                self.baseline[fp] = BaselineFinding(
                    fingerprint=fp,
                    rule_id=finding.get('rule_id', ''),
                    file=finding.get('file', ''),
                    line=finding.get('line', 0),
                    tool=finding.get('tool', ''),
                    first_seen=now,
                    last_seen=now,
                    status='open'
                )
            else:
                # Existing finding
                baseline_f = self.baseline[fp]
                
                if baseline_f.status == 'open':
                    # Update last_seen
                    baseline_f.last_seen = now
                    # Report based on policy: new in PR context even if in baseline
                    finding['is_new'] = False
                else:
                    # Fixed, wont_fix, or false_positive - skip
                    finding['is_new'] = False
        
        self._save_baseline()
        return new_findings
    
    def mark_fixed(self, fingerprint: str):
        """Mark a finding as fixed"""
        if fingerprint in self.baseline:
            self.baseline[fingerprint].status = 'fixed'
            self._save_baseline()
    
    def mark_suppressed(self, fingerprint: str, justification: str):
        """Mark a finding as suppressed/wont_fix"""
        if fingerprint in self.baseline:
            self.baseline[fingerprint].status = 'wont_fix'
            self.baseline[fingerprint].justification = justification
            self._save_baseline()
    
    def get_baseline_stats(self) -> Dict[str, int]:
        """Get statistics about baseline findings"""
        by_status = {}
        for finding in self.baseline.values():
            by_status[finding.status] = by_status.get(finding.status, 0) + 1
        
        return {
            'total': len(self.baseline),
            **by_status
        }


class DeduplicationManager:
    """Deduplicates findings from multiple tools"""
    
    @staticmethod
    def deduplicate_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate findings from multiple tools reporting the same issue.
        
        Strategy:
        1. Group by file, line, and approximate message
        2. Keep the highest confidence/severity version
        3. Merge tool information
        """
        
        # Group by location
        by_location = {}
        for finding in findings:
            key = (finding['file'], finding['line'])
            
            if key not in by_location:
                by_location[key] = []
            by_location[key].append(finding)
        
        deduped = []
        for location_findings in by_location.values():
            if len(location_findings) == 1:
                deduped.append(location_findings[0])
            else:
                # Multiple findings at same location
                merged = DeduplicationManager._merge_findings(location_findings)
                deduped.append(merged)
        
        return deduped
    
    @staticmethod
    def _merge_findings(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple findings at same location"""
        
        # Sort by severity/confidence
        severity_order = {'critical': 0, 'major': 1, 'minor': 2, 'info': 3}
        findings = sorted(
            findings,
            key=lambda f: severity_order.get(f.get('severity', 'info'), 999)
        )
        
        primary = findings[0].copy()
        
        # Merge tool insights
        tools = set()
        for f in findings:
            tools.add(f.get('tool', 'unknown'))
        
        primary['tools'] = list(tools)
        primary['duplicate_count'] = len(findings)
        
        if len(findings) > 1:
            primary['message'] += f"\n(Reported by {len(tools)} tools: {', '.join(sorted(tools))})"
        
        return primary


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Baseline and Deduplication Manager")
    parser.add_argument("--results", required=True, help="Path to review-results.json")
    parser.add_argument("--baseline", default=".review-baseline.json", help="Baseline file")
    parser.add_argument("--output", required=True, help="Output file for processed findings")
    
    args = parser.parse_args()
    
    # Load results
    with open(args.results, 'r') as f:
        results = json.load(f)
    
    if results['status'] != 'success':
        print("Results indicate failure; skipping processing")
        return
    
    findings = results.get('findings', [])
    
    # Deduplicate
    print("Deduplicating findings from multiple tools...")
    deduped = DeduplicationManager.deduplicate_findings(findings)
    print(f"  Reduced from {len(findings)} to {len(deduped)} findings")
    
    # Apply baseline filtering
    print("Filtering against baseline...")
    baseline_mgr = BaselineManager(args.baseline)
    new_findings = baseline_mgr.filter_new_findings(deduped)
    
    stats = baseline_mgr.get_baseline_stats()
    print(f"Baseline stats: {stats}")
    print(f"  New findings this run: {len(new_findings)}")
    
    # Save processed results
    results['findings'] = new_findings
    results['deduplication'] = {
        'original_count': len(findings),
        'after_dedup': len(deduped),
        'new_findings': len(new_findings)
    }
    
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✓ Processed results saved to {args.output}")


if __name__ == "__main__":
    main()
