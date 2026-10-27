"""Próbka ERS (osobny moduł, żeby laps.py i ers.py nie importowały się nawzajem)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ErsSample:
    distance_m: float
    store_j: float
    deployed_j: float  # narastająco od startu okrążenia
    harvested_j: float
    deploy_mode: int
