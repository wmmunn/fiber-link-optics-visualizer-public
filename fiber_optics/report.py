from __future__ import annotations

from datetime import datetime
import html

from .models import DirectionReading, EndpointReading, MetricReading


def _format_time(value: datetime) -> str:
    return value.strftime("%B %d, %Y at %I:%M:%S %p %Z").replace(" 0", " ")


def _short_time(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S %Z")


def _number(value: float) -> str:
    return f"{value:.2f}"


def _overall_status(endpoints: tuple[EndpointReading, EndpointReading]) -> str:
    levels = {reading.level for endpoint in endpoints for reading in endpoint.metrics}
    if "alarm" in levels:
        return "Alarm"
    if "warn" in levels:
        return "Warning"
    return "Healthy"


def _scale(reading: MetricReading, value: float) -> float:
    span = reading.high_alarm - reading.low_alarm
    if span <= 0:
        return 50.0
    scale_min = reading.low_alarm - (span * 0.15)
    scale_max = reading.high_alarm + (span * 0.15)
    return max(0.0, min(100.0, ((value - scale_min) / (scale_max - scale_min)) * 100.0))


def _zones(reading: MetricReading) -> tuple[float, float, float, float, float]:
    low_alarm = _scale(reading, reading.low_alarm)
    low_warn = _scale(reading, reading.low_warn)
    high_warn = _scale(reading, reading.high_warn)
    high_alarm = _scale(reading, reading.high_alarm)
    return (
        low_alarm,
        max(0.0, low_warn - low_alarm),
        max(0.0, high_warn - low_warn),
        max(0.0, high_alarm - high_warn),
        max(0.0, 100.0 - high_alarm),
    )


def _range_bar(reading: MetricReading) -> str:
    alarm_low, warn_low, normal, warn_high, alarm_high = _zones(reading)
    marker = _scale(reading, reading.value)
    return (
        "<div class='range'>"
        f"<i class='zone alarm' style='width:{alarm_low:.2f}%'></i>"
        f"<i class='zone warning' style='width:{warn_low:.2f}%'></i>"
        f"<i class='zone normal' style='width:{normal:.2f}%'></i>"
        f"<i class='zone warning' style='width:{warn_high:.2f}%'></i>"
        f"<i class='zone alarm' style='width:{alarm_high:.2f}%'></i>"
        f"<b class='marker' style='left:{marker:.2f}%'></b>"
        "</div>"
        "<div class='range-labels'>"
        f"<span>{reading.low_alarm:.2f} alarm</span>"
        f"<span>{reading.low_warn:.2f} warn</span>"
        f"<span>{reading.high_warn:.2f} warn</span>"
        f"<span>{reading.high_alarm:.2f} alarm</span>"
        "</div>"
    )


def _endpoint_panel(endpoint: EndpointReading, css_class: str) -> str:
    graph_rows = []
    detail_rows = []
    for reading in endpoint.metrics:
        graph_rows.append(
            f"<tr class='row-{reading.level}'>"
            f"<td class='metric'>{html.escape(reading.metric)}</td>"
            f"<td class='value'>{_number(reading.value)} {html.escape(reading.unit)}</td>"
            f"<td class='range-cell'>{_range_bar(reading)}</td>"
            "</tr>"
        )
        detail_rows.append(
            "<tr>"
            f"<td>{html.escape(reading.metric)}</td>"
            f"<td>{_number(reading.value)} {html.escape(reading.unit)}</td>"
            f"<td>{_number(reading.low_alarm)}</td>"
            f"<td>{_number(reading.low_warn)}</td>"
            f"<td>{_number(reading.high_warn)}</td>"
            f"<td>{_number(reading.high_alarm)}</td>"
            "</tr>"
        )

    return f"""
<article class="panel {css_class}">
  <div class="panel-head">
    <h2>{html.escape(endpoint.label)}</h2>
    <div class="endpoint-meta">{html.escape(endpoint.device)} &middot; {html.escape(endpoint.interface)} &middot; Cisco Catalyst</div>
    <div class="endpoint-time">Collected: {html.escape(_short_time(endpoint.collected_at))}</div>
  </div>
  <table>
    <thead><tr><th>Metric</th><th>Value</th><th>Device Threshold Range</th></tr></thead>
    <tbody>{''.join(graph_rows)}</tbody>
  </table>
  <div class="data-points">
    <div class="data-points-title">Actual Data Points</div>
    <table>
      <thead><tr><th>Metric</th><th>Value</th><th>Low Alarm</th><th>Low Warn</th><th>High Warn</th><th>High Alarm</th></tr></thead>
      <tbody>{''.join(detail_rows)}</tbody>
    </table>
  </div>
</article>
"""


def _direction_card(direction: DirectionReading, reverse: bool) -> str:
    status_labels = {
        "ok": "READINGS OK",
        "warn": "WARNING",
        "alarm": "ALARM",
        "missing": "DATA MISSING",
    }
    tx_value = f"{direction.tx.value:.2f}" if direction.tx else "n/a"
    rx_value = f"{direction.rx.value:.2f}" if direction.rx else "n/a"
    loss = f"{direction.loss_db:.2f} dB" if direction.loss_db is not None else "Unavailable"
    arrow = "&#9664;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;" if reverse else "&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9472;&#9654;"
    left_label = (
        f"{direction.destination_label.replace('Endpoint ', '')} receive"
        if reverse
        else f"{direction.source_label.replace('Endpoint ', '')} transmit"
    )
    right_label = (
        f"{direction.source_label.replace('Endpoint ', '')} transmit"
        if reverse
        else f"{direction.destination_label.replace('Endpoint ', '')} receive"
    )
    left_value = rx_value if reverse else tx_value
    right_value = tx_value if reverse else rx_value
    return f"""
<article class="direction-card direction-{direction.status}">
  <div class="direction-head">
    <span>{html.escape(direction.label)}</span>
    <span class="status-pill">{status_labels[direction.status]}</span>
  </div>
  <div class="arrow">{arrow}</div>
  <div class="direction-values">
    <div><small>{html.escape(left_label)}</small><div class="reading">{left_value}</div></div>
    <div>{'&larr;' if reverse else '&rarr;'}</div>
    <div><small>{html.escape(right_label)}</small><div class="reading">{right_value}</div></div>
  </div>
  <div class="loss"><small>Estimated optical loss</small><strong>{loss}</strong></div>
</article>
"""


def build_html_report(
    endpoint_a: EndpointReading,
    endpoint_b: EndpointReading,
    directions: tuple[DirectionReading, DirectionReading],
) -> str:
    status = _overall_status((endpoint_a, endpoint_b))
    latest = max(endpoint_a.collected_at, endpoint_b.collected_at)
    timestamp_note = (
        f"Endpoint A: {endpoint_a.timestamp_source}; "
        f"Endpoint B: {endpoint_b.timestamp_source}"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fiber Link Optics Report</title>
<style>
:root{{--ink:#22313a;--muted:#63727a;--line:#c9d3d7;--panel:#fff;--page:#eef2f3;--ok:#bfe8c4;--ok-soft:#eef8ef;--warn:#ffe19a;--alarm:#f4b4ad;--blue:#236b8e;--blue-soft:#e9f4f9}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--page);color:var(--ink);font-family:"Segoe UI",Arial,sans-serif}} main{{max-width:1500px;margin:0 auto;padding:28px}}
header{{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;margin-bottom:18px}} h1{{margin:0 0 5px;font-size:28px}} .subtitle{{color:var(--muted);font-size:14px}}
.mode{{padding:7px 11px;border:1px solid #8eb8cb;border-radius:999px;background:var(--blue-soft);color:#164e69;font-size:12px;font-weight:700;white-space:nowrap}}
.summary{{display:grid;grid-template-columns:repeat(3,minmax(150px,1fr));gap:10px;margin-bottom:14px}} .summary-card{{padding:12px 14px;border:1px solid var(--line);border-radius:8px;background:var(--panel)}}
.summary-label{{color:var(--muted);font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}} .summary-value{{margin-top:4px;font-size:16px;font-weight:700}}
.Healthy{{color:#246635}} .Warning{{color:#805c00}} .Alarm{{color:#8b211b}}
.collection-banner{{display:flex;justify-content:center;gap:9px;align-items:baseline;margin-bottom:14px;padding:11px 14px;border:1px solid #8eb8cb;border-radius:8px;background:var(--blue-soft);color:#164e69}}
.collection-banner span{{font-size:11px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}} .collection-banner strong{{font-size:17px}} .collection-banner small{{color:var(--muted)}}
.link-layout{{display:grid;grid-template-columns:minmax(390px,1fr) minmax(245px,.62fr) minmax(390px,1fr);gap:14px;align-items:stretch}}
.panel{{overflow:hidden;border:1px solid var(--line);border-radius:10px;background:var(--panel);box-shadow:0 2px 8px rgba(33,49,58,.06)}} .panel-head{{padding:14px 16px;border-bottom:1px solid var(--line);background:#f8fafb}}
.panel-head h2{{margin:0;font-size:18px}} .endpoint-meta{{margin-top:4px;color:var(--muted);font-size:12px}} .endpoint-time{{margin-top:5px;color:#315b70;font-size:10px;font-weight:700}}
table{{width:100%;border-collapse:collapse}} th,td{{padding:10px 8px;border-bottom:1px solid #e1e7e9;text-align:left;vertical-align:middle;font-size:12px}} th{{background:#f3f6f7;color:#4a5b64;font-size:10px;letter-spacing:.04em;text-transform:uppercase}}
tr:last-child td{{border-bottom:0}} .metric{{width:76px;font-weight:700}} .value{{width:72px;font-variant-numeric:tabular-nums;white-space:nowrap}} .range-cell{{min-width:190px}}
.range{{position:relative;display:flex;height:18px;overflow:hidden;border:1px solid #89979d;border-radius:4px}} .zone{{height:100%}} .alarm{{background:var(--alarm)}} .warning{{background:var(--warn)}} .normal{{background:var(--ok)}}
.marker{{position:absolute;top:-3px;width:3px;height:24px;background:#111;box-shadow:0 0 0 1px #fff}} .range-labels{{display:flex;justify-content:space-between;margin-top:3px;color:var(--muted);font-size:8px;font-variant-numeric:tabular-nums}}
.row-ok td{{background:var(--ok-soft)}} .row-warn td{{background:#fff7d8}} .row-alarm td{{background:#ffe0dc}}
.data-points{{margin:14px;overflow:hidden;border:1px solid var(--line);border-radius:7px}} .data-points-title{{padding:8px 10px;border-bottom:1px solid var(--line);background:#f3f6f7;color:#4a5b64;font-size:10px;font-weight:800;letter-spacing:.05em;text-transform:uppercase}}
.data-points th,.data-points td{{padding:6px 7px;font-size:10px;font-variant-numeric:tabular-nums;white-space:nowrap;text-align:right}} .data-points th{{font-size:8px}} .data-points th:first-child,.data-points td:first-child{{text-align:left}} .data-points tbody tr:nth-child(even) td{{background:#f8fafb}}
.directions{{display:flex;flex-direction:column;justify-content:center;gap:16px;padding:16px;border:1px solid var(--line);border-radius:10px;background:#f8fafb}} .directions-title{{text-align:center;color:var(--muted);font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}}
.direction-card{{padding:14px;border:1px solid #a9c8d8;border-radius:9px;background:var(--blue-soft)}} .direction-warn{{border-color:#d8b75c;background:#fff8dd}} .direction-alarm{{border-color:#d48a83;background:#fff0ee}} .direction-missing{{border-color:#b5bec2;background:#f1f3f4}}
.direction-head{{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:14px;font-weight:800}} .status-pill{{padding:3px 7px;border-radius:999px;background:#d9efdc;color:#246635;font-size:10px}} .direction-warn .status-pill{{background:#ffe19a;color:#694f18}} .direction-alarm .status-pill{{background:#f4b4ad;color:#7a1d17}} .direction-missing .status-pill{{background:#dfe4e6;color:#4f5b57}}
.arrow{{margin:12px 0;color:var(--blue);font-size:26px;font-weight:700;letter-spacing:2px;text-align:center}} .direction-values{{display:grid;grid-template-columns:1fr auto 1fr;gap:7px;align-items:center;text-align:center}} .direction-values small{{display:block;color:var(--muted);font-size:9px;font-weight:700;text-transform:uppercase}}
.reading{{margin-top:2px;font-size:16px;font-weight:800}} .loss{{margin-top:12px;padding-top:10px;border-top:1px solid #bfd3dc;text-align:center}} .loss strong{{display:block;margin-top:2px;font-size:23px;color:#164e69}}
.note{{margin-top:14px;padding:11px 13px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--muted);font-size:11px}} footer{{margin-top:12px;color:var(--muted);font-size:10px;text-align:right}}
@media(max-width:1050px){{.link-layout{{grid-template-columns:1fr}} .directions{{order:2}} .endpoint-b{{order:3}} .summary{{grid-template-columns:1fr}}}}
</style>
</head>
<body><main>
<header><div><h1>Fiber Link Optics Report</h1><div class="subtitle">Bidirectional DOM review for a Cisco Catalyst fiber link</div></div><div class="mode">MANUAL LOG IMPORT</div></header>
<section class="summary">
  <div class="summary-card"><div class="summary-label">Overall status</div><div class="summary-value {status}">{status}</div></div>
  <div class="summary-card"><div class="summary-label">Endpoint A</div><div class="summary-value">{html.escape(endpoint_a.device)} &middot; {html.escape(endpoint_a.interface)}</div></div>
  <div class="summary-card"><div class="summary-label">Endpoint B</div><div class="summary-value">{html.escape(endpoint_b.device)} &middot; {html.escape(endpoint_b.interface)}</div></div>
</section>
<div class="collection-banner"><span>Latest data timestamp</span><strong>{html.escape(_format_time(latest))}</strong><small>manual import</small></div>
<section class="link-layout">
{_endpoint_panel(endpoint_a, "endpoint-a")}
<section class="directions"><div class="directions-title">Fiber Directions</div>{_direction_card(directions[0], False)}{_direction_card(directions[1], True)}</section>
{_endpoint_panel(endpoint_b, "endpoint-b")}
</section>
<div class="note">Directional loss is estimated from device-reported Tx and remote Rx values. It is not an OTDR measurement and cannot locate a loss event along the fiber path.</div>
<footer>Timestamp sources: {html.escape(timestamp_note)} &middot; Input files: {html.escape(endpoint_a.source_file)}, {html.escape(endpoint_b.source_file)}</footer>
</main></body></html>
"""
