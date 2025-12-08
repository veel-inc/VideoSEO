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

from abc import ABC, abstractmethod
from typing import Any, Dict


class TrendingSearchPort(ABC):
    """
    Abstract port interface for retrieving current trending search data.

    This abstract base class defines the contract that input adapters must implement
    to provide trending search terms and associated metadata to the application.
    Implementations should return trend information in a stable, serializable
    structure so higher-level components can consume it without depending on
    source-specific details.

    Methods
    -------
    async get_current_search_trends(limit: int = 20, min_score: float = 0.0) -> Dict[str, Any]
        Retrieve current trending search entries.

        Args:
            limit: Maximum number of trend entries to return. Defaults to 20.
            min_score: Minimum relevance or popularity score for an entry to be included.
                Entries with scores below this threshold should be filtered out.
                Defaults to 0.0.

        Returns:
            A dictionary containing trend results and related metadata. Common keys
            (implementations should document exact shapes) may include:
                - "items": List of trend entry dicts/objects (each typically containing
                  at least 'term' and 'score' fields).
                - "total": Integer total number of available trends (before applying
                  limit/min_score).
                - "source": Optional identifier of the data source.
                - "timestamp": Optional retrieval time as an ISO 8601 string or datetime.

        Raises:
            Implementation-specific exceptions for network, parsing, or authentication
            errors. Callers should handle these according to their retry/error policies.

    Notes:
        - Implementations must be asynchronous and non-blocking.
        - Concrete adapters should document the exact structure of each trend entry to
          ensure consumers can interpret fields consistently.
    """

    @abstractmethod
    async def get_current_search_trends(
        self, limit: int = 20, min_score: float = 0.0
    ) -> Dict[str, Any]:
        pass
