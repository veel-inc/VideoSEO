# Copyright (C) 2025 Veel Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.adapters import (
    AsyncOpenAIApiAdapter,
    AsyncPostgresDatabaseAdapter,
    TrendingSearchAdapter,
)

logger = logging.getLogger(__name__)


class TrendingSearchScheduler:
    """
    Scheduler for periodic execution of trending search pipeline.
    Manages the lifecycle of the batch processing.
    """

    def __init__(self, interval_minutes: int = 15):
        """
        Initialize the scheduler.

        Args:
            interval_minutes: How often to run the pipeline (default: 15)
        """
        self.interval_minutes = interval_minutes
        self.scheduler = AsyncIOScheduler()
        self._is_running = False

    def start(self):
        """Start the scheduler."""
        try:
            if self._is_running:
                logger.warning("Scheduler is already running")
                return

            # Schedule the job
            self.scheduler.add_job(
                self._run_pipeline,
                trigger=IntervalTrigger(minutes=self.interval_minutes),
                id="trending_search_batch",
                name="Trending Search Batch Processing",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )

            self.scheduler.start()
            self._is_running = True

            logger.info(
                f"Trending search scheduler started "
                f"(interval: {self.interval_minutes} min)"
            )

        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            raise

    async def _run_pipeline(self):
        """Execute a single pipeline run."""
        try:
            logger.info("=" * 70)
            logger.info(f"Scheduled pipeline execution started")
            logger.info(f"Timestamp: {datetime.now(timezone.utc)}")

            # Initialize ports
            database_port = AsyncPostgresDatabaseAdapter()
            openai_port = AsyncOpenAIApiAdapter()

            # Create pipeline adapter
            pipeline = TrendingSearchAdapter(
                database_port=database_port, openai_client_port=openai_port
            )

            # Run pipeline
            result = await pipeline.run_batch_pipeline()

            logger.info(f"Pipeline completed: {result}")
            logger.info("=" * 70)

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)

    def stop(self):
        """Stop the scheduler gracefully."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                self._is_running = False
                logger.info("Trending search scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._is_running
