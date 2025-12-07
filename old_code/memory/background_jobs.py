"""Background job system for memory operations."""

import logging
import threading
import time
import queue
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class JobType(Enum):
    """Types of background jobs."""
    COMPRESS_CONVERSATION = "compress_conversation"
    EXTRACT_FACTS = "extract_facts"
    PROMOTE_STM_TO_LTM = "promote_stm_to_ltm"
    DECAY_STM = "decay_stm"
    PRUNE_OLD_MEMORIES = "prune_old_memories"
    UPDATE_ACCESS_COUNT = "update_access_count"


@dataclass
class BackgroundJob:
    """Background job definition."""
    job_type: JobType
    params: Dict[str, Any]
    priority: int = 5  # 1=highest, 10=lowest
    callback: Optional[Callable] = None
    
    def __lt__(self, other):
        """Compare jobs by priority for priority queue ordering."""
        if not isinstance(other, BackgroundJob):
            return NotImplemented
        return self.priority < other.priority


class BackgroundJobQueue:
    """
    Background job queue for memory operations.
    
    Features:
    - Priority queue for job scheduling
    - Worker thread pool for parallel execution
    - Non-blocking job submission
    - Graceful shutdown
    
    Design:
    - Memory compression and fact extraction run in background
    - STM/LTM creation happens asynchronously
    - Doesn't block user queries
    """
    
    def __init__(self, num_workers: int = 2, max_queue_size: int = 100):
        """
        Initialize background job queue.
        
        Args:
            num_workers: Number of worker threads (default: 2)
            max_queue_size: Maximum queue size (default: 100)
        """
        self.num_workers = num_workers
        self.max_queue_size = max_queue_size
        
        # Priority queue (lower priority number = higher priority)
        self.job_queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_queue_size)
        
        # Worker threads
        self.workers: list[threading.Thread] = []
        self.running = False
        
        # Job handlers
        self.handlers: Dict[JobType, Callable] = {}
        
        # Statistics
        self.jobs_completed = 0
        self.jobs_failed = 0
        self.lock = threading.Lock()
        
        logger.info(f"✅ BackgroundJobQueue initialized (workers={num_workers})")
    
    def register_handler(self, job_type: JobType, handler: Callable):
        """
        Register a handler for specific job type.
        
        Args:
            job_type: Type of job
            handler: Callable that processes the job
        """
        self.handlers[job_type] = handler
        logger.debug(f"📝 Registered handler for {job_type.value}")
    
    def submit(self, job: BackgroundJob) -> bool:
        """
        Submit a job to the queue.
        
        Args:
            job: BackgroundJob to execute
            
        Returns:
            True if submitted successfully, False if queue is full
        """
        try:
            # Use priority for ordering (lower number = higher priority)
            self.job_queue.put_nowait((job.priority, time.time(), job))
            logger.debug(f"📥 Job queued: {job.job_type.value} (priority={job.priority})")
            return True
        except queue.Full:
            logger.warning(f"⚠️  Job queue full, dropping job: {job.job_type.value}")
            return False
    
    def start(self):
        """Start worker threads."""
        if self.running:
            logger.warning("⚠️  Job queue already running")
            return
        
        self.running = True
        
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"MemoryJobWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"🚀 Started {self.num_workers} background job workers")
    
    def stop(self, timeout: float = 5.0):
        """Stop worker threads gracefully."""
        if not self.running:
            return
        
        logger.info("🛑 Stopping background job workers...")
        self.running = False
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=timeout)
        
        self.workers.clear()
        logger.info("✅ Background job workers stopped")
    
    def _worker_loop(self):
        """Worker thread main loop."""
        worker_name = threading.current_thread().name
        logger.debug(f"🔧 {worker_name} started")
        
        while self.running:
            try:
                # Get job with timeout to allow checking self.running
                try:
                    priority, timestamp, job = self.job_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Execute job
                logger.debug(f"⚙️  {worker_name} processing: {job.job_type.value}")
                start_time = time.time()
                
                try:
                    # Get handler for job type
                    handler = self.handlers.get(job.job_type)
                    if handler:
                        result = handler(**job.params)
                        
                        # Call callback if provided
                        if job.callback:
                            job.callback(result)
                        
                        elapsed = time.time() - start_time
                        logger.debug(f"✅ {job.job_type.value} completed in {elapsed:.2f}s")
                        
                        with self.lock:
                            self.jobs_completed += 1
                    else:
                        logger.error(f"❌ No handler for job type: {job.job_type.value}")
                        with self.lock:
                            self.jobs_failed += 1
                
                except Exception as e:
                    logger.error(f"❌ Job failed: {job.job_type.value} - {e}", exc_info=True)
                    with self.lock:
                        self.jobs_failed += 1
                
                finally:
                    self.job_queue.task_done()
            
            except Exception as e:
                logger.error(f"❌ Worker error: {e}", exc_info=True)
        
        logger.debug(f"🔧 {worker_name} stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self.lock:
            return {
                'queue_size': self.job_queue.qsize(),
                'jobs_completed': self.jobs_completed,
                'jobs_failed': self.jobs_failed,
                'workers': self.num_workers,
                'running': self.running
            }
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"<BackgroundJobQueue workers={stats['workers']} "
            f"queue={stats['queue_size']} "
            f"completed={stats['jobs_completed']} "
            f"failed={stats['jobs_failed']}>"
        )
