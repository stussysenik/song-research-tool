import threading
import time
import heapq
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Tuple

logger = logging.getLogger(__name__)

class PriorityLevel(Enum):
    HIGH = 0
    MEDIUM = 1
    LOW = 2

@dataclass(order=True)
class PrioritizedItem:
    priority: int
    timestamp: float = field(default_factory=time.time)
    item: Any = field(compare=False)

class SmartDownloadQueue:
    """Smart queue for managing downloads with prioritization and rate limiting."""
    
    def __init__(self, max_concurrent=3, rate_limit=5):
        self.queue = []  # Priority queue
        self.in_progress = {}  # task_id -> task_info
        self.results = {}  # task_id -> result
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit  # downloads per minute
        self.last_download_times = []
        self.lock = threading.RLock()
        self.not_empty = threading.Condition(self.lock)
        self.not_full = threading.Condition(self.lock)
        self.all_done = threading.Event()
        self.shutdown_flag = False
    
    def add_task(self, task_id, task_data, priority=PriorityLevel.MEDIUM):
        """Add a task to the queue with the specified priority."""
        with self.lock:
            # Create a prioritized item
            item = PrioritizedItem(
                priority=priority.value,
                timestamp=time.time(),
                item={"id": task_id, "data": task_data}
            )
            
            # Add to queue
            heapq.heappush(self.queue, item)
            
            # Signal that the queue is not empty
            self.not_empty.notify()
            
            logger.info(f"Added task {task_id} with priority {priority.name}")
            return task_id
    
    def get_next_task(self, blocking=True):
        """Get the next task from the queue."""
        with self.lock:
            # Check if we're at max concurrent tasks
            while len(self.in_progress) >= self.max_concurrent:
                if not blocking:
                    return None
                self.not_full.wait()
                
                if self.shutdown_flag:
                    return None
            
            # Check if we need to wait due to rate limiting
            now = time.time()
            self.last_download_times = [t for t in self.last_download_times if now - t < 60]
            
            if len(self.last_download_times) >= self.rate_limit:
                # Wait until we can perform another download
                sleep_time = 60 - (now - self.last_download_times[0])
                if sleep_time > 0:
                    if not blocking:
                        return None
                    self.not_empty.wait(sleep_time)
            
            # Get the next task
            while len(self.queue) > 0:
                item = heapq.heappop(self.queue)
                task_id = item.item["id"]
                
                # Check if this task is already completed or in progress
                if task_id in self.results or task_id in self.in_progress:
                    continue
                    
                # Mark as in progress
                self.in_progress[task_id] = {
                    "data": item.item["data"],
                    "start_time": now,
                    "priority": item.priority
                }
                
                # Update rate limiting
                self.last_download_times.append(now)
                
                logger.info(f"Starting task {task_id}")
                return task_id, item.item["data"]
            
            # No tasks available
            if not blocking:
                return None
                
            # Wait for tasks to be added
            self.not_empty.wait()
            
            if self.shutdown_flag:
                return None
                
            # Retry after waiting
            return self.get_next_task(blocking)
    
    def complete_task(self, task_id, result):
        """Mark a task as complete with its result."""
        with self.lock:
            # Remove from in-progress
            if task_id in self.in_progress:
                del self.in_progress[task_id]
                
                # Store result
                self.results[task_id] = {
                    "result": result,
                    "completion_time": time.time()
                }
                
                # Signal that there's space for another task
                self.not_full.notify()
                
                logger.info(f"Completed task {task_id}")
                
                # Check if all tasks are done
                if len(self.in_progress) == 0 and len(self.queue) == 0:
                    self.all_done.set()
            else:
                logger.warning(f"Task {task_id} was not in progress")
    
    def get_result(self, task_id):
        """Get the result of a completed task."""
        with self.lock:
            if task_id in self.results:
                return self.results[task_id]["result"]
            return None
    
    def get_status(self, task_id=None):
        """Get status of a specific task or all tasks."""
        with self.lock:
            if task_id:
                # Specific task status
                if task_id in self.results:
                    return {
                        "status": "completed",
                        "result": self.results[task_id]["result"]
                    }
                elif task_id in self.in_progress:
                    return {
                        "status": "in_progress",
                        "start_time": self.in_progress[task_id]["start_time"],
                        "elapsed": time.time() - self.in_progress[task_id]["start_time"]
                    }
                else:
                    # Check if it's in the queue
                    for item in self.queue:
                        if item.item["id"] == task_id:
                            return {
                                "status": "queued",
                                "priority": PriorityLevel(item.priority).name,
                                "queue_time": item.timestamp
                            }
                    return {"status": "not_found"}
            else:
                # Overall stats
                return {
                    "queued": len(self.queue),
                    "in_progress": len(self.in_progress),
                    "completed": len(self.results),
                    "rate_limit_status": {
                        "recent_downloads": len(self.last_download_times),
                        "limit": self.rate_limit
                    }
                }
    
    def wait_for_completion(self, timeout=None):
        """Wait for all tasks to complete."""
        return self.all_done.wait(timeout)
        
    def shutdown(self):
        """Shut down the queue."""
        with self.lock:
            self.shutdown_flag = True
            self.not_empty.notify_all()
            self.not_full.notify_all() 