"""Duplicate Resolution Strategies for Import Hub.

Provides multiple strategies to handle records with identical hashes 
within the same import batch, replacing the standard silent 'drop' behavior.
"""

import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

class DuplicateResolver:
    
    def __init__(self, strategy: str = "drop"):
        """
        Strategies:
        - 'drop': Discard all subsequent identical records.
        - 'keep_latest': Overwrite previous occurrences if newer (simulated via list order).
        - 'sum': Add their values together (useful if tracking distinct events grouped identically).
        - 'flag_only': Do not remove them, just flag them with a warning for manual review.
        """
        valid_strategies = {"drop", "keep_latest", "sum", "flag_only"}
        if strategy not in valid_strategies:
            logger.warning(f"Unknown duplicate strategy '{strategy}', defaulting to 'drop'.")
            self.strategy = "drop"
        else:
            self.strategy = strategy
            
    def resolve(self, records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Apply the chosen duplicate resolution strategy.
        
        Assumes records have already been passed through DataCleaner and have a '_hash' key.
        """
        stats = {"duplicates_processed": 0, "strategy_applied": self.strategy}
        
        if not records:
            return records, stats
            
        if self.strategy == "flag_only":
            seen_hashes = set()
            for r in records:
                h = r.get("_hash")
                if not h:
                    continue
                if h in seen_hashes:
                    if "_warnings" not in r:
                        r["_warnings"] = []
                    r["_warnings"].append("[DUPLICATE] This record is identical to a prior record.")
                    stats["duplicates_processed"] += 1
                else:
                    seen_hashes.add(h)
            return records, stats
            
        if self.strategy == "drop":
            seen_hashes = set()
            resolved = []
            for r in records:
                h = r.get("_hash")
                if not h:
                    resolved.append(r)
                    continue
                if h in seen_hashes:
                    stats["duplicates_processed"] += 1
                else:
                    seen_hashes.add(h)
                    resolved.append(r)
            return resolved, stats
            
        if self.strategy == "keep_latest":
            # Just keep the last occurrence in the list
            hash_map = {}
            unhashed = []
            for r in records:
                h = r.get("_hash")
                if h:
                    if h in hash_map:
                        stats["duplicates_processed"] += 1
                    hash_map[h] = r
                else:
                    unhashed.append(r)
                    
            resolved = list(hash_map.values()) + unhashed
            return resolved, stats
            
        if self.strategy == "sum":
            hash_map = {}
            unhashed = []
            for r in records:
                h = r.get("_hash")
                if h:
                    if h in hash_map:
                        # Sum the values
                        existing = hash_map[h]
                        existing_val = existing.get("value", 0.0)
                        new_val = r.get("value", 0.0)
                        if existing_val is not None and new_val is not None:
                            existing["value"] = existing_val + new_val
                            
                            # Also sum normalized if present
                            if "normalized_value" in existing and "normalized_value" in r:
                                existing["normalized_value"] += r["normalized_value"]
                            
                            if "_warnings" not in existing:
                                existing["_warnings"] = []
                            msg = "[SUMMED] Added values from duplicate record."
                            if msg not in existing.get("_warnings", []):
                                existing["_warnings"].append(msg)
                                
                        stats["duplicates_processed"] += 1
                    else:
                        hash_map[h] = r
                else:
                    unhashed.append(r)
                    
            resolved = list(hash_map.values()) + unhashed
            return resolved, stats
            
        return records, stats
