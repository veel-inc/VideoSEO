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
