from collections import Counter
from typing import Callable, Protocol, Sequence


class MoodCheckinLike(Protocol):
    mood_id: str
    mood_label: str


def average(values: list[int]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def describe_mood_pattern(checkins: Sequence[MoodCheckinLike]) -> str:
    if not checkins:
        return 'No data'

    labels = [item.mood_label for item in checkins if item.mood_label]
    if not labels:
        return 'Mixed'

    counts = Counter(labels)
    top_count = max(counts.values())
    leaders = [label for label, count in counts.items() if count == top_count]
    if len(leaders) > 1:
        return 'Mixed'
    if top_count == 1 and len(labels) > 1:
        return 'Mixed'
    return f'Mostly {leaders[0].lower()}'


def build_trend_summary_data(
    checkins: Sequence[MoodCheckinLike],
    score_for_mood: Callable[[str], int],
) -> dict[str, str | float | None]:
    scored = [score_for_mood(item.mood_id) for item in checkins]
    latest = checkins[-1].mood_label if checkins else None

    if len(scored) < 4:
        return {
            'label': 'Not enough data',
            'direction': 'neutral',
            'detail': 'Keep checking in to reveal a clearer pattern.',
            'average_score': average(scored),
            'latest_mood_label': latest,
        }

    midpoint = len(scored) // 2
    first_half = average(scored[:midpoint])
    second_half = average(scored[midpoint:])
    delta = second_half - first_half

    if delta >= 0.45 and second_half >= 3.0:
        return {
            'label': 'Improving',
            'direction': 'up',
            'detail': 'Recent check-ins are trending calmer and more positive.',
            'average_score': average(scored),
            'latest_mood_label': latest,
        }
    if delta >= 0.45:
        return {
            'label': 'Early shift',
            'direction': 'up_soft',
            'detail': 'Your recent check-ins look a little less intense, but still on the hard side.',
            'average_score': average(scored),
            'latest_mood_label': latest,
        }
    if delta <= -0.45:
        return {
            'label': 'Declining',
            'direction': 'down',
            'detail': 'Recent check-ins are trending lower than the earlier part of this range.',
            'average_score': average(scored),
            'latest_mood_label': latest,
        }
    return {
        'label': 'Stable',
        'direction': 'steady',
        'detail': 'Your mood has been relatively consistent in this range.',
        'average_score': average(scored),
        'latest_mood_label': latest,
    }
