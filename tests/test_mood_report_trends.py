from datetime import date, datetime, timezone

from app.services.mood_reporting import build_trend_summary_data, describe_mood_pattern


MOOD_SCORES = {
    'overwhelmed': 1,
    'confused': 2,
    'okay': 3,
    'better': 4,
    'calm': 5,
}


class Checkin:
    def __init__(self, mood_id: str, mood_label: str, day: int, item_id: int):
        self.id = item_id
        self.user_id = 1
        self.mood_id = mood_id
        self.mood_label = mood_label
        self.checkin_date = date(2026, 4, day)
        self.created_at = datetime(2026, 4, day, 12, 0, tzinfo=timezone.utc)
        self.updated_at = self.created_at


def score_for_mood(mood_id: str) -> int:
    return MOOD_SCORES[mood_id]


def make_checkin(mood_id: str, mood_label: str, day: int, item_id: int) -> Checkin:
    stamp = datetime(2026, 4, day, 12, 0, tzinfo=timezone.utc)
    item = Checkin(mood_id, mood_label, day, item_id)
    item.created_at = stamp
    item.updated_at = stamp
    return item


def test_guarded_improvement_stays_early_shift_for_low_scores() -> None:
    checkins = [
        make_checkin('overwhelmed', 'Overwhelmed', 1, 1),
        make_checkin('confused', 'Confused', 2, 2),
        make_checkin('confused', 'Confused', 3, 3),
        make_checkin('confused', 'Confused', 4, 4),
    ]

    summary = build_trend_summary_data(checkins, score_for_mood)

    assert summary['label'] == 'Early shift'
    assert summary['direction'] == 'up_soft'
    assert summary['average_score'] == 1.75


def test_clear_improvement_requires_recent_scores_to_reach_moderate_range() -> None:
    checkins = [
        make_checkin('overwhelmed', 'Overwhelmed', 1, 1),
        make_checkin('confused', 'Confused', 2, 2),
        make_checkin('okay', 'Okay', 3, 3),
        make_checkin('better', 'Better', 4, 4),
    ]

    summary = build_trend_summary_data(checkins, score_for_mood)

    assert summary['label'] == 'Improving'
    assert summary['direction'] == 'up'
    assert summary['average_score'] == 2.5


def test_flat_low_scores_are_stable() -> None:
    checkins = [
        make_checkin('confused', 'Confused', 1, 1),
        make_checkin('confused', 'Confused', 2, 2),
        make_checkin('confused', 'Confused', 3, 3),
        make_checkin('confused', 'Confused', 4, 4),
    ]

    summary = build_trend_summary_data(checkins, score_for_mood)

    assert summary['label'] == 'Stable'
    assert summary['direction'] == 'steady'


def test_declining_scores_are_marked_declining() -> None:
    checkins = [
        make_checkin('better', 'Better', 1, 1),
        make_checkin('okay', 'Okay', 2, 2),
        make_checkin('confused', 'Confused', 3, 3),
        make_checkin('overwhelmed', 'Overwhelmed', 4, 4),
    ]

    summary = build_trend_summary_data(checkins, score_for_mood)

    assert summary['label'] == 'Declining'
    assert summary['direction'] == 'down'


def test_short_sequences_return_not_enough_data() -> None:
    checkins = [
        make_checkin('overwhelmed', 'Overwhelmed', 1, 1),
        make_checkin('confused', 'Confused', 2, 2),
        make_checkin('confused', 'Confused', 3, 3),
    ]

    summary = build_trend_summary_data(checkins, score_for_mood)

    assert summary['label'] == 'Not enough data'
    assert summary['direction'] == 'neutral'


def test_pattern_descriptor_uses_dominant_mood_not_trend_label() -> None:
    checkins = [
        make_checkin('overwhelmed', 'Overwhelmed', 1, 1),
        make_checkin('confused', 'Confused', 2, 2),
        make_checkin('confused', 'Confused', 3, 3),
        make_checkin('confused', 'Confused', 4, 4),
    ]

    summary = build_trend_summary_data(checkins, score_for_mood)

    assert summary['label'] == 'Early shift'
    assert describe_mood_pattern(checkins) == 'Mostly confused'
