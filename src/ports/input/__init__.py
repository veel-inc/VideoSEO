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

from src.ports.input.video_seo_query_port import VideoSEOQueryPort
from src.ports.input.health_service_port import HealthServicePort
from src.ports.input.trending_search_port import TrendingSearchPort

__all__ = ["VideoSEOQueryPort", "HealthServicePort", "TrendingSearchPort"]