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

from unittest.mock import AsyncMock

import pytest

from src.adapters import VideoSEOQueryAdapter


@pytest.mark.asyncio
async def test_async_get_video_seo_query():
    mock_db = AsyncMock()
    mock_openai = AsyncMock()

    mock_openai.text_embedding.return_value = [[0.1] * 1536]
    mock_db.search_similar_vectors.return_value = [
        {
            "video_id": "123",
            "segment_text": "Some text",
            "segment_start_time": 0.0,
            "segment_end_time": 10.0,
            "distance": 0.1,
        }
    ]
    mock_db.insert_into_session_table.return_value = None

    adapter = VideoSEOQueryAdapter(
        database_port=mock_db, openai_client_port=mock_openai
    )

    result = await adapter.async_get_video_seo_query("test query")
    assert isinstance(result, dict)
    assert result["status"] == "Success"
    assert len(result["results"]) == 1

    result_empty = await adapter.async_get_video_seo_query("")
    assert result_empty["status"] == "Error"
    assert result_empty["results"] == []
    assert "empty" in result_empty["error"]

    mock_openai.text_embedding.return_value = []
    result_no_embed = await adapter.async_get_video_seo_query("some query")
    assert result_no_embed["status"] == "Error"
    assert result_no_embed["results"] == []
    assert "Embedding" in result_no_embed["error"]
