import time

from ..metrics import MetricsCollector


def test_metrics_collector_tracks_counters_and_durations():
    collector = MetricsCollector(ttl_seconds=10)
    collector.increment("workflows_started")
    collector.increment("workflows_started", 2)
    collector.observe_duration("workflow_latency", 0.2)
    collector.observe_duration("workflow_latency", 0.4)

    snapshot = collector.export()

    assert snapshot["counters"]["workflows_started"] == 3
    averages = collector.timer_averages()
    assert 0.29 < averages["workflow_latency"] < 0.31


def test_metrics_collector_prunes_old_samples():
    collector = MetricsCollector(ttl_seconds=1)
    collector.observe_duration("workflow_latency", 0.1)
    time.sleep(1.1)
    collector.observe_duration("workflow_latency", 0.2)

    timeline = list(collector.timeline("workflow_latency"))
    assert len(timeline) == 1
