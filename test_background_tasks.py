import time
import pytest
from background_tasks import (
    submit_background_task,
    get_task,
    clear_background_task,
    TaskStatus,
    BackgroundTask
)

def dummy_slow_function(x, y):
    time.sleep(0.1)
    return x + y

def dummy_error_function():
    raise ValueError("Test error in background thread")

def dummy_progress_function(progress_callback=None):
    if progress_callback:
        progress_callback(0.5, "Halfway done")
    time.sleep(0.05)
    if progress_callback:
        progress_callback(1.0, "All done")
    return "SUCCESS"


def test_submit_background_task_success():
    task_key = "test_task_success"
    task = submit_background_task(task_key, dummy_slow_function, 10, 20, task_name="Slow Add")
    
    assert task.status in [TaskStatus.RUNNING, TaskStatus.COMPLETED]
    
    # Wait for completion
    task.future.result(timeout=2.0)
    
    assert task.status == TaskStatus.COMPLETED
    assert task.result == 30
    assert task.progress == 1.0
    
    clear_background_task(task_key)
    assert get_task(task_key) is None


def test_submit_background_task_error():
    task_key = "test_task_error"
    task = submit_background_task(task_key, dummy_error_function, task_name="Error Task")
    
    # Wait for completion
    task.future.result(timeout=2.0)
    
    assert task.status == TaskStatus.FAILED
    assert "Test error in background thread" in task.error
    
    clear_background_task(task_key)


def test_submit_background_task_progress():
    task_key = "test_task_progress"
    task = submit_background_task(task_key, dummy_progress_function, task_name="Progress Task")
    
    task.future.result(timeout=2.0)
    
    assert task.status == TaskStatus.COMPLETED
    assert task.result == "SUCCESS"
    assert task.progress == 1.0
    
    clear_background_task(task_key)
