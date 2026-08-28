"""
Asynchronous Data Processing Utilities
Purpose: Use async operations to process large datasets faster and avoid blocking.
"""

import asyncio
import time
from typing import List, Dict, Any, Callable


async def process_row_async(row: Dict[str, Any], processor: Callable) -> Dict[str, Any]:
    """
    Asynchronously processes a single row of data.
    """
    # Simulate I/O bound operation
    await asyncio.sleep(0.01)
    try:
        return processor(row)
    except Exception as e:
        return {"error": str(e), "row": row}


async def process_dataset_async(data: List[Dict[str, Any]], processor: Callable) -> List[Dict[str, Any]]:
    """
    Processes a large dataset concurrently using asyncio.gather.
    """
    tasks = [process_row_async(row, processor) for row in data]
    results = await asyncio.gather(*tasks)
    return list(results)


def process_dataset_sync(data: List[Dict[str, Any]], processor: Callable) -> List[Dict[str, Any]]:
    """
    Processes a large dataset sequentially (for comparison).
    """
    results = []
    for row in data:
        try:
            results.append(processor(row))
        except Exception as e:
            results.append({"error": str(e), "row": row})
    return results


def run_async_processor(data: List[Dict[str, Any]], processor: Callable) -> List[Dict[str, Any]]:
    """
    Runs the asynchronous processor and returns the result.
    """
    return asyncio.run(process_dataset_async(data, processor))