from __future__ import annotations

import json

from .base import human_ticket
from leo_go_trading.planner import StrategyPlan


def preview(plan: StrategyPlan, json_output: bool = False) -> str:
    if json_output:
        return json.dumps(plan.as_dict(), indent=2, sort_keys=True)
    return human_ticket(plan)
