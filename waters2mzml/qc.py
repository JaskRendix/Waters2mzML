from dataclasses import dataclass


@dataclass
class QCResult:
    tic: list[float]
    bpc: list[float]
    peak_counts: list[int]
