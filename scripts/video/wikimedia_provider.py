"""Re-export Wikimedia provider — implementação em media_providers."""

from scripts.video.media_providers.wikimedia_provider import (
    create_ken_burns_video,
    download_first_image,
    search_wikimedia,
    test_wikimedia_search,
)

__all__ = [
    "search_wikimedia",
    "download_first_image",
    "create_ken_burns_video",
    "test_wikimedia_search",
]
