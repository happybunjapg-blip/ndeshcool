from datetime import timedelta
from typing import Dict, Optional
from backend.state import AppState


class AnalyticsService:
    def __init__(self, state: AppState):
        self.state = state

    def current_vs_previous(self, period: str) -> Dict:
        length = self.state.period_length_days(period)
        cur_start, cur_end = self.state.period_dates(period)
        prev_end = cur_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=length - 1)
        current = self.state.calculate_period_metrics(cur_start, cur_end)
        previous = self.state.calculate_period_metrics(prev_start, prev_end)
        return {"current": current, "previous": previous}

    def trend(self, current: float, previous: float, invert: bool = False) -> Optional[str]:
        return self.state.trend_str(current, previous, invert=invert)
