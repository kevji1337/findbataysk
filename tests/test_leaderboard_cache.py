from bot.services.leaderboard_cache import (
    get_cached_leaderboard_text,
    invalidate_leaderboard_cache,
    set_cached_leaderboard_text,
)


def test_leaderboard_cache_set_get_and_invalidate():
    period = "week"
    payload = "cached leaderboard payload"

    set_cached_leaderboard_text(period, payload)
    assert get_cached_leaderboard_text(period) == payload

    invalidate_leaderboard_cache()
    assert get_cached_leaderboard_text(period) is None
