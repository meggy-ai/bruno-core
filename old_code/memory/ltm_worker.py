"""
Long-term memory worker for automatic STM to LTM promotion.

This module provides a background worker that continuously monitors
short-term memories (STM) and automatically promotes eligible entries
to long-term memory (LTM) based on configurable criteria.

Design:
- Runs as a separate background thread
- Periodic checks for STM promotion candidates (default: every 5 minutes)
- Uses MemoryRetriever.suggest_ltm_candidates() for eligibility
- Promotes via ContextCompressor.promote_to_ltm()
- Integrates with BackgroundJobQueue for job management
- Configurable promotion criteria (age, access count, relevance)
"""

import logging
import threading
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

from bruno.memory.memory_retriever import MemoryRetriever
from bruno.memory.context_compressor import ContextCompressor
from bruno.memory.background_jobs import BackgroundJobQueue, BackgroundJob, JobType

logger = logging.getLogger(__name__)


class LTMWorkerConfig:
    """Configuration for LTM worker."""
    
    def __init__(
        self,
        check_interval_seconds: int = 300,  # 5 minutes
        min_access_count: int = 3,
        min_relevance: float = 0.8,
        min_age_days: float = 3.0,
        batch_size: int = 10,
        consolidate_memories: bool = True,
        enable_auto_promotion: bool = True
    ):
        """
        Initialize LTM worker configuration.
        
        Args:
            check_interval_seconds: How often to check for candidates (default: 300s = 5min)
            min_access_count: Minimum times accessed for promotion (default: 3)
            min_relevance: Minimum relevance score (default: 0.8)
            min_age_days: Minimum age in days (default: 3.0)
            batch_size: Maximum memories to promote per batch (default: 10)
            consolidate_memories: Whether to consolidate related memories (default: True)
            enable_auto_promotion: Master switch for auto-promotion (default: True)
        """
        self.check_interval_seconds = check_interval_seconds
        self.min_access_count = min_access_count
        self.min_relevance = min_relevance
        self.min_age_days = min_age_days
        self.batch_size = batch_size
        self.consolidate_memories = consolidate_memories
        self.enable_auto_promotion = enable_auto_promotion


class LTMWorker:
    """
    Background worker for automatic STM to LTM promotion.
    
    This worker:
    - Runs continuously in a background thread
    - Periodically checks for STM entries eligible for promotion
    - Submits promotion jobs to BackgroundJobQueue
    - Tracks statistics on promotions
    - Can be paused/resumed without stopping
    """
    
    def __init__(
        self,
        memory_retriever: MemoryRetriever,
        context_compressor: ContextCompressor,
        job_queue: BackgroundJobQueue,
        config: Optional[LTMWorkerConfig] = None
    ):
        """
        Initialize LTM worker.
        
        Args:
            memory_retriever: For finding promotion candidates
            context_compressor: For promoting STM to LTM
            job_queue: For background job processing
            config: Worker configuration (uses defaults if None)
        """
        self.memory_retriever = memory_retriever
        self.context_compressor = context_compressor
        self.job_queue = job_queue
        self.config = config or LTMWorkerConfig()
        
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False
        self.paused = False
        
        # Statistics
        self.stats = {
            'checks_performed': 0,
            'candidates_found': 0,
            'promotions_attempted': 0,
            'promotions_succeeded': 0,
            'last_check': None,
            'last_promotion': None,
        }
        
        # Register promotion job handler
        self._register_promotion_handler()
        
        logger.info("🔧 LTM Worker initialized with config:")
        logger.info(f"   - Check interval: {self.config.check_interval_seconds}s")
        logger.info(f"   - Min access count: {self.config.min_access_count}")
        logger.info(f"   - Min relevance: {self.config.min_relevance}")
        logger.info(f"   - Min age: {self.config.min_age_days} days")
        logger.info(f"   - Auto-promotion: {self.config.enable_auto_promotion}")
    
    def _register_promotion_handler(self):
        """Register handler for PROMOTE_STM_TO_LTM jobs."""
        def promotion_handler(stm_entries: List[Dict[str, Any]], consolidate: bool = True):
            """
            Handle STM to LTM promotion job.
            
            Args:
                stm_entries: List of STM dictionaries to promote
                consolidate: Whether to consolidate related memories
            """
            try:
                if not stm_entries:
                    logger.warning("⚠️ Promotion job has no STM entries")
                    return
                
                logger.info(f"🔄 Processing promotion job: {len(stm_entries)} STM entries")
                
                promoted_count = self.context_compressor.promote_to_ltm(
                    stm_entries=stm_entries,
                    consolidate=consolidate
                )
                
                self.stats['promotions_attempted'] += len(stm_entries)
                self.stats['promotions_succeeded'] += promoted_count
                self.stats['last_promotion'] = datetime.now()
                
                logger.info(f"✅ Promotion job complete: {promoted_count} entries promoted to LTM")
                return {'promoted_count': promoted_count}
                
            except Exception as e:
                logger.error(f"❌ Promotion job failed: {e}", exc_info=True)
                raise
        
        self.job_queue.register_handler(JobType.PROMOTE_STM_TO_LTM, promotion_handler)
        logger.info("📝 Registered handler for PROMOTE_STM_TO_LTM jobs")
    
    def start(self):
        """Start the LTM worker thread."""
        if self.running:
            logger.warning("⚠️ LTM Worker already running")
            return
        
        self.running = True
        self.paused = False
        
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            name="LTMWorker",
            daemon=True
        )
        self.worker_thread.start()
        
        logger.info("🚀 LTM Worker started")
    
    def stop(self, timeout: float = 5.0):
        """
        Stop the LTM worker thread.
        
        Args:
            timeout: Maximum time to wait for thread shutdown (seconds)
        """
        if not self.running:
            logger.warning("⚠️ LTM Worker not running")
            return
        
        logger.info("🛑 Stopping LTM Worker...")
        self.running = False
        
        if self.worker_thread and threading.current_thread() != self.worker_thread:
            self.worker_thread.join(timeout=timeout)
        
        logger.info("✅ LTM Worker stopped")
    
    def pause(self):
        """Pause the LTM worker (stops checking but keeps thread alive)."""
        if not self.running:
            logger.warning("⚠️ Cannot pause - LTM Worker not running")
            return
        
        self.paused = True
        logger.info("⏸️ LTM Worker paused")
    
    def resume(self):
        """Resume the LTM worker."""
        if not self.running:
            logger.warning("⚠️ Cannot resume - LTM Worker not running")
            return
        
        self.paused = False
        logger.info("▶️ LTM Worker resumed")
    
    def _worker_loop(self):
        """Main worker loop that runs in background thread."""
        logger.info("🔄 LTM Worker loop started")
        
        while self.running:
            try:
                if not self.paused and self.config.enable_auto_promotion:
                    self._check_and_promote()
                
                # Sleep in small intervals to allow responsive shutdown
                for _ in range(self.config.check_interval_seconds):
                    if not self.running:
                        break
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Error in LTM worker loop: {e}", exc_info=True)
                time.sleep(10)  # Back off on error
        
        logger.info("🔄 LTM Worker loop ended")
    
    def _check_and_promote(self):
        """Check for promotion candidates and submit jobs."""
        try:
            logger.debug("🔍 Checking for STM promotion candidates...")
            
            # Find candidates using MemoryRetriever
            candidates = self.memory_retriever.suggest_ltm_candidates(
                min_access_count=self.config.min_access_count,
                min_relevance=self.config.min_relevance,
                age_days=self.config.min_age_days
            )
            
            self.stats['checks_performed'] += 1
            self.stats['candidates_found'] += len(candidates)
            self.stats['last_check'] = datetime.now()
            
            if not candidates:
                logger.debug("✅ No STM candidates found for promotion")
                return
            
            # Batch candidates and submit jobs
            batch_size = self.config.batch_size
            for i in range(0, len(candidates), batch_size):
                batch = candidates[i:i + batch_size]
                
                job = BackgroundJob(
                    job_type=JobType.PROMOTE_STM_TO_LTM,
                    params={
                        'stm_entries': batch,
                        'consolidate': self.config.consolidate_memories
                    },
                    priority=5  # Medium priority
                )
                
                submitted = self.job_queue.submit(job)
                
                if submitted:
                    logger.info(f"📤 Submitted promotion job for {len(batch)} STM entries")
                else:
                    logger.warning(f"⚠️ Failed to submit promotion job for {len(batch)} entries")
            
        except Exception as e:
            logger.error(f"❌ Error checking for promotions: {e}", exc_info=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get worker statistics.
        
        Returns:
            Dictionary with worker stats
        """
        stats = self.stats.copy()
        stats['running'] = self.running
        stats['paused'] = self.paused
        stats['config'] = {
            'check_interval': self.config.check_interval_seconds,
            'min_access_count': self.config.min_access_count,
            'min_relevance': self.config.min_relevance,
            'min_age_days': self.config.min_age_days,
            'batch_size': self.config.batch_size,
            'consolidate': self.config.consolidate_memories,
            'enabled': self.config.enable_auto_promotion
        }
        return stats
    
    def trigger_check(self):
        """Manually trigger a promotion check (useful for testing)."""
        if not self.running:
            logger.warning("⚠️ Cannot trigger check - LTM Worker not running")
            return
        
        logger.info("🔧 Manually triggering promotion check...")
        self._check_and_promote()
    
    def update_config(self, **kwargs):
        """
        Update worker configuration at runtime.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"🔧 Updated config: {key} = {value}")
            else:
                logger.warning(f"⚠️ Unknown config parameter: {key}")
    
    def __repr__(self) -> str:
        """String representation."""
        status = "running" if self.running else "stopped"
        if self.running and self.paused:
            status = "paused"
        
        return (
            f"<LTMWorker status={status} "
            f"checks={self.stats['checks_performed']} "
            f"promoted={self.stats['promotions_succeeded']}>"
        )
