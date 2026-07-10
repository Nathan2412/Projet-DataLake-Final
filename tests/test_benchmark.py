from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1] / "scripts"))
import benchmark_endpoints as target


def _fake_post_factory(calls, timing, statuses=None):
    def fake_post_json(url: str, payload: dict, timeout: int):
        calls.append((url, payload, timeout))
        batch_size = len(payload["data"]["tickers"])
        endpoint = "ingest_fast" if "/ingest_fast" in url else "ingest"
        duration = timing[batch_size].pop(0)
        status = statuses[batch_size][endpoint]
        return {"status": status, "errors": []}, duration

    return fake_post_json


def test_benchmark_repeats_and_alternating_order_and_payload_equality() -> None:
    calls = []
    timing = {
        1: [0.030, 0.020, 0.040, 0.060, 0.050, 0.010],
        100: [0.120, 0.100, 0.070, 0.080, 0.040, 0.095],
    }
    statuses = {
        1: {"ingest": "standard", "ingest_fast": "fast"},
        100: {"ingest": "standard", "ingest_fast": "fast"},
    }

    with patch.object(target, "post_json", side_effect=_fake_post_factory(calls, timing, statuses)):
        report = target.benchmark("http://localhost:8000/", period="5d", repeats=3, timeout=123)

    assert report["repeats"] == 3
    assert [result["batch_size"] for result in report["results"]] == [1, 100]
    assert len(calls) == 12

    batch1, batch100 = report["results"]
    assert [s["execution_order"] for s in batch1["samples"]] == ["standard-first", "fast-first", "standard-first"]
    assert [s["execution_order"] for s in batch100["samples"]] == ["standard-first", "fast-first", "standard-first"]

    expected_payload_1 = {"data": {"tickers": ["AAPL"], "period": "5d", "run_staging": True, "run_curated": True}}
    expected_payload_100 = {"data": {"tickers": target.TICKERS_100[:100], "period": "5d", "run_staging": True, "run_curated": True}}

    for sample in batch1["samples"]:
        assert sample["payload"] == expected_payload_1
        assert sample["payload"]["data"]["tickers"] == ["AAPL"]
        assert sample["payload"]["data"].get("use_cache") is None

    for sample in batch100["samples"]:
        assert sample["payload"] == expected_payload_100
        assert sample["payload"]["data"]["tickers"] == target.TICKERS_100[:100]
        assert sample["payload"]["data"].get("use_cache") is None

    assert batch1["standard_wall_ms_median"] == 50.0
    assert batch1["fast_wall_ms_median"] == 20.0
    assert batch1["gain_pct_median"] == 60.0
    assert batch1["target_met"] is True

    assert batch100["target_met"] is False


def test_benchmark_metadata_fields() -> None:
    calls = []
    timing = {1: [0.1, 0.1, 0.2, 0.2, 0.05, 0.05], 100: [1.0, 0.5, 1.1, 0.7, 0.9, 0.4]}
    statuses = {
        1: {"ingest": "ok", "ingest_fast": "ok"},
        100: {"ingest": "ok", "ingest_fast": "ok"},
    }

    with patch.object(target, "post_json", side_effect=_fake_post_factory(calls, timing, statuses)):
        report = target.benchmark("http://localhost:8000", period="1mo", repeats=3, timeout=60)

    assert report["base_url"] == "http://localhost:8000"
    assert report["period"] == "1mo"
    assert report["repeats"] == 3
    assert report["cache_enabled"] is False
    assert report["target_gain_pct"] == 30
    assert isinstance(report["python_version"], str) and report["python_version"]
    assert isinstance(report["platform"], str) and report["platform"]
    assert isinstance(report["git_commit"], str)
