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

import asyncio
import logging

logger = logging.getLogger(__name__)


class MaterializedViewRefreshScheduler:
    def __init__(self, database_adapter, interval_minutes: int = 15):
        self.database_adapter = database_adapter
        self.interval = interval_minutes
        self._task: asyncio.Task | None = None
        self.is_running = False

    async def _run(self):

        logger.info("Materialized view scheduler started")
        try:
            while True:
                try:
                    logger.info("Refreshing materialized view")
                    await self.database_adapter.refresh_materialized_view_tables()
                    logger.info("Materialized view refresh completed")
                except Exception as e:
                    logger.exception("Materialized view refresh failed", exc_info=e)

                await asyncio.sleep(self.interval * 60)

        except asyncio.CancelledError:
            logger.info("Materialized view scheduler cancelled")
            raise

    def start(self):
        if self.is_running:
            return

        self.is_running = True
        self._task = asyncio.create_task(self._run())

    def stop(self):
        if self._task:
            self._task.cancel()
            self.is_running = False
