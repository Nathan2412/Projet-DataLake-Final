"""Benchmark reproductible des endpoints /ingest et /ingest_fast."""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


TICKERS_100 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JPM", "JNJ",
    "V", "PG", "XOM", "UNH", "MA", "HD", "CVX", "MRK", "ABBV", "KO",
    "PEP", "COST", "AVGO", "LLY", "WMT", "BAC", "MCD", "CSCO", "TMO", "ACN",
    "CRM", "ABT", "DHR", "LIN", "CMCSA", "NKE", "TXN", "PM", "NEE", "ORCL",
    "AMD", "UPS", "RTX", "HON", "QCOM", "LOW", "AMGN", "IBM", "INTC", "CAT",
    "SPGI", "GS", "BLK", "DE", "SBUX", "INTU", "ISRG", "MDT", "GILD", "BKNG",
    "ADP", "TJX", "NOC", "ADI", "VRTX", "LMT", "SYK", "REGN", "PGR", "CB",
    "SCHW", "AMT", "C", "MO", "ZTS", "SO", "DUK", "PLD", "CI", "BDX",
    "CME", "USB", "CL", "TGT", "EL", "MMM", "FIS", "ITW", "CSX", "NSC",
    "GM", "F", "MU", "PANW", "SNPS", "CDNS", "KLAC", "MCK", "MAR", "AON",
]


def post_json(url: str, payload: dict[str, Any], timeout: int) -> tuple[dict, float]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    with urlopen(request, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result, time.perf_counter() - started


def get_git_commit(base_path: str = ".") -> str:
    try:
        result = subprocess.run(
            ["git", "-C", base_path, "rev-parse", "HEAD"],
            check=False,
            text=True,
            capture_output=True,
            timeout=1,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _call_api(url: str, payload: dict[str, Any], timeout: int) -> tuple[str, list[str], float]:
    try:
        result, wall = post_json(url, payload, timeout)
        return str(result.get("status", "")), list(result.get("errors", [])), round(wall * 1000, 2)
    except Exception as exc:
        return "error", [str(exc)], 0.0


def _format_payload(period: str, batch_size: int) -> dict[str, Any]:
    return {
        "data": {
            "tickers": TICKERS_100[:batch_size],
            "period": period,
            "run_staging": True,
            "run_curated": True,
        }
    }


def _build_sample(base_url: str, payload: dict[str, Any], timeout: int, fast_first: bool) -> dict[str, Any]:
    if fast_first:
        fast_status, fast_errors, fast_wall = _call_api(f"{base_url}/ingest_fast", payload, timeout)
        standard_status, standard_errors, standard_wall = _call_api(f"{base_url}/ingest", payload, timeout)
        execution_order = "fast-first"
    else:
        standard_status, standard_errors, standard_wall = _call_api(f"{base_url}/ingest", payload, timeout)
        fast_status, fast_errors, fast_wall = _call_api(f"{base_url}/ingest_fast", payload, timeout)
        execution_order = "standard-first"

    return {
        "payload": payload,
        "execution_order": execution_order,
        "standard_wall_ms": standard_wall,
        "fast_wall_ms": fast_wall,
        "standard_status": standard_status,
        "fast_status": fast_status,
        "standard_errors": standard_errors,
        "fast_errors": fast_errors,
    }


def _median(values: list[float]) -> float:
    return round(statistics.median(values), 2) if values else 0.0


def _batch_report(base_url: str, period: str, batch_size: int, repeats: int, timeout: int) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    payload = _format_payload(period, batch_size)

    for repeat_index in range(repeats):
        samples.append(_build_sample(base_url, payload, timeout, repeat_index % 2 == 1))

    standard_statuses = [sample["standard_status"] for sample in samples]
    fast_statuses = [sample["fast_status"] for sample in samples]
    standard_wall_ms_median = _median([sample["standard_wall_ms"] for sample in samples])
    fast_wall_ms_median = _median([sample["fast_wall_ms"] for sample in samples])
    gain_pct_median = round(
        100.0 * (standard_wall_ms_median - fast_wall_ms_median) / standard_wall_ms_median,
        2,
    ) if standard_wall_ms_median else 0.0

    target_gain_pct = 30
    valid = all(
        sample["standard_status"] == "success"
        and sample["fast_status"] == "success"
        and not sample["standard_errors"]
        and not sample["fast_errors"]
        for sample in samples
    )

    return {
        "batch_size": batch_size,
        "repeats": repeats,
        "samples": samples,
        "standard_wall_ms_median": standard_wall_ms_median,
        "fast_wall_ms_median": fast_wall_ms_median,
        "gain_pct_median": gain_pct_median,
        "target_gain_pct": target_gain_pct,
        "valid": valid,
        "target_met": valid and gain_pct_median >= target_gain_pct,
        "standard_statuses": standard_statuses,
        "fast_statuses": fast_statuses,
    }


def benchmark(base_url: str, period: str, repeats: int, timeout: int) -> dict[str, Any]:
    return {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "period": period,
        "repeats": repeats,
        "cache_enabled": False,
        "python_version": sys.version,
        "platform": platform.platform(),
        "git_commit": get_git_commit(),
        "results": [_batch_report(base_url, period, size, repeats, timeout) for size in (1, 100)],
        "target_gain_pct": 30,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--period", default="5d")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", default="benchmarks/benchmark_results.json")
    args = parser.parse_args()

    report = benchmark(
        args.base_url.rstrip("/"),
        args.period,
        max(1, args.repeats),
        args.timeout,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
