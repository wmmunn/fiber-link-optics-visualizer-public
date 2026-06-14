from __future__ import annotations

from .models import DirectionReading, EndpointReading


def build_direction(
    label: str,
    source: EndpointReading,
    destination: EndpointReading,
) -> DirectionReading:
    tx = source.metric("Tx Power")
    rx = destination.metric("Rx Power")
    loss = tx.value - rx.value if tx is not None and rx is not None else None
    return DirectionReading(
        label=label,
        source_label=source.label,
        destination_label=destination.label,
        tx=tx,
        rx=rx,
        loss_db=loss,
    )
