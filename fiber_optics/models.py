from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MetricReading:
    metric: str
    unit: str
    value: float
    low_alarm: float
    low_warn: float
    high_warn: float
    high_alarm: float

    @property
    def level(self) -> str:
        if self.value <= self.low_alarm or self.value >= self.high_alarm:
            return "alarm"
        if self.value <= self.low_warn or self.value >= self.high_warn:
            return "warn"
        return "ok"


@dataclass(frozen=True)
class EndpointReading:
    label: str
    device: str
    interface: str
    collected_at: datetime
    timestamp_source: str
    source_file: str
    metrics: tuple[MetricReading, ...]

    def metric(self, name: str) -> MetricReading | None:
        return next((reading for reading in self.metrics if reading.metric == name), None)


@dataclass(frozen=True)
class DirectionReading:
    label: str
    source_label: str
    destination_label: str
    tx: MetricReading | None
    rx: MetricReading | None
    loss_db: float | None

    @property
    def status(self) -> str:
        if self.tx is None or self.rx is None:
            return "missing"
        if self.tx.level == "alarm" or self.rx.level == "alarm":
            return "alarm"
        if self.tx.level == "warn" or self.rx.level == "warn":
            return "warn"
        return "ok"
