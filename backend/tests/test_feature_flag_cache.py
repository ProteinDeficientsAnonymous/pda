"""resolve_flags() is cached only inside an explicit cached_flags() scope.

A flag is a kill switch, so caching it ambiently would let a long-lived process
(a management command, a worker loop) serve a stale value indefinitely.
"""

import pytest
from community.models import (
    FeatureFlag,
    FeatureFlagState,
    cached_flags,
    clear_flag_cache,
    flag_enabled,
    resolve_flags,
)

FLAG = FeatureFlag.EVENT_PAYMENT_CONFIRMATION


@pytest.fixture(autouse=True)
def _clean_cache():
    clear_flag_cache()
    yield
    clear_flag_cache()


@pytest.mark.django_db
class TestCachedFlagsScope:
    def test_repeated_calls_inside_the_scope_hit_the_db_once(self, django_assert_num_queries):
        with django_assert_num_queries(1), cached_flags():
            for _ in range(10):
                resolve_flags()

    def test_flag_enabled_shares_the_cache(self, django_assert_num_queries):
        with django_assert_num_queries(1), cached_flags():
            flag_enabled(FLAG)
            flag_enabled(FeatureFlag.HOST_ATTENDANCE_REPORT)
            flag_enabled(FLAG)

    def test_leaving_the_scope_drops_the_cache(self, django_assert_num_queries):
        with cached_flags():
            resolve_flags()
        with django_assert_num_queries(1):
            resolve_flags()

    def test_uncached_outside_the_scope(self, django_assert_num_queries):
        """The default has to stay uncached — a cron loop must see a toggle."""
        with django_assert_num_queries(3):
            resolve_flags()
            resolve_flags()
            resolve_flags()

    def test_a_toggle_is_visible_to_the_next_scope(self):
        with cached_flags():
            assert flag_enabled(FLAG) is False

        FeatureFlagState.objects.update_or_create(key=FLAG, defaults={"enabled": True})

        with cached_flags():
            assert flag_enabled(FLAG) is True

    def test_a_toggle_mid_scope_is_deliberately_not_seen(self):
        """The scope freezes flags for its lifetime — that's the tradeoff for one query."""
        with cached_flags():
            assert flag_enabled(FLAG) is False
            FeatureFlagState.objects.update_or_create(key=FLAG, defaults={"enabled": True})
            assert flag_enabled(FLAG) is False

    def test_explicit_clear_re_reads_within_a_scope(self):
        with cached_flags():
            assert flag_enabled(FLAG) is False
            FeatureFlagState.objects.update_or_create(key=FLAG, defaults={"enabled": True})
            clear_flag_cache()
            assert flag_enabled(FLAG) is True

    def test_nesting_reuses_the_outer_entry(self, django_assert_num_queries):
        with django_assert_num_queries(1), cached_flags():
            with cached_flags():
                resolve_flags()
            resolve_flags()

    def test_an_exception_still_clears_the_cache(self, django_assert_num_queries):
        with pytest.raises(RuntimeError), cached_flags():
            resolve_flags()
            raise RuntimeError("boom")
        with django_assert_num_queries(1):
            resolve_flags()

    def test_db_override_still_beats_the_code_default(self):
        FeatureFlagState.objects.update_or_create(key=FLAG, defaults={"enabled": True})
        with cached_flags():
            assert resolve_flags()[FLAG] is True

    def test_clear_on_a_cold_cache_is_a_no_op(self):
        clear_flag_cache()
        clear_flag_cache()
        assert resolve_flags() is not None
