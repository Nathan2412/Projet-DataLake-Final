import os
import tempfile
import unittest

import numpy as np
import pandas as pd

from ingestion.ingest_api import index_api_data_to_es
from ingestion.ingest_file import index_to_elasticsearch, load_file_dataset, raw_document_id
from transformation.curated.transform_curated import classify_anomaly_type
from transformation.staging.transform_staging import add_technical_indicators, calc_rsi, prepare_staging_dataframe
from unittest.mock import MagicMock, patch


class FinancialIndicatorTests(unittest.TestCase):
    def make_frame(self) -> pd.DataFrame:
        close = np.linspace(100.0, 160.0, 80) + np.sin(np.arange(80))
        return pd.DataFrame(
            {
                "ticker": "TEST",
                "date": pd.date_range("2024-01-01", periods=80),
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "adj_close": close,
                "volume": np.arange(80) + 1_000,
            }
        )

    def test_fast_indicators_match_standard_pipeline(self):
        frame = self.make_frame()
        standard = add_technical_indicators(frame.copy())
        fast = prepare_staging_dataframe(frame)
        for column in (
            "sma_20",
            "sma_50",
            "ema_12",
            "ema_26",
            "rsi_14",
            "macd",
            "macd_signal",
            "bollinger_upper",
            "bollinger_lower",
            "daily_return",
            "volatility_20",
        ):
            pd.testing.assert_series_equal(standard[column], fast[column], check_names=False)

    def test_daily_return_uses_previous_close(self):
        frame = self.make_frame().iloc[:3].copy()
        frame["close"] = [100.0, 110.0, 121.0]
        result = prepare_staging_dataframe(frame)["daily_return"]
        self.assertAlmostEqual(result.iloc[1], 0.10)
        self.assertAlmostEqual(result.iloc[2], 0.10)

    def test_rsi_handles_monotonic_and_flat_series(self):
        rising = calc_rsi(pd.Series(np.arange(1.0, 40.0)))
        flat = calc_rsi(pd.Series(np.ones(40)))
        self.assertEqual(rising.iloc[-1], 100.0)
        self.assertEqual(flat.iloc[-1], 50.0)


class FileDatasetTests(unittest.TestCase):
    def test_load_file_dataset_normalizes_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "finance.csv")
            pd.DataFrame(
                [
                    {"Ticker": "aapl", "Date": "2024-01-02", "Open": 1, "High": 2, "Low": 1, "Close": 2, "Volume": 10},
                    {"Ticker": "AAPL", "Date": "2024-01-02", "Open": 2, "High": 3, "Low": 2, "Close": 3, "Volume": 20},
                ]
            ).to_csv(path, index=False)
            result = load_file_dataset(path)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "ticker"], "AAPL")
        self.assertEqual(result.loc[0, "adj_close"], 3)

    def test_load_file_dataset_rejects_missing_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "invalid.csv")
            pd.DataFrame([{"ticker": "AAPL", "date": "2024-01-02"}]).to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "Colonnes manquantes"):
                load_file_dataset(path)


class CuratedLogicTests(unittest.TestCase):
    def test_classify_flash_crash(self):
        row = pd.Series({"is_anomaly": True, "daily_return": -0.08, "volume_zscore": 1, "volatility_20": 0.02})
        self.assertEqual(classify_anomaly_type(row), "flash_crash")


class RawDocumentAndStagingTests(unittest.TestCase):
    def test_raw_document_id_is_source_ticker_date(self):
        self.assertEqual(raw_document_id("yfinance_fast", "aapl", "2024-01-02"), "yfinance_fast_aapl_2024-01-02")

    def test_prepare_staging_dataframe_normalizes_ticker_and_drops_duplicates(self):
        prepared = prepare_staging_dataframe(
            pd.DataFrame(
                [
                    {"ticker": " aapl ", "date": "2024-01-02", "open": 1, "high": 2, "low": 1, "close": 2, "adj_close": 2, "volume": 10},
                    {"ticker": "AAPL", "date": "2024-01-02", "open": 2, "high": 3, "low": 1.5, "close": 5, "adj_close": 5, "volume": 20},
                ]
            )
        )
        self.assertEqual(prepared.loc[0, "ticker"], "AAPL")
        self.assertEqual(len(prepared), 1)

    def test_file_and_api_indexing_use_source_specific_raw_document_id(self):
        rows = [
            {"ticker": "AAPL", "date": "2024-01-02", "open": 1, "high": 2, "low": 1, "close": 2, "adj_close": 2, "volume": 10}
        ]
        df = pd.DataFrame(rows)
        with patch("ingestion.ingest_file.helpers.bulk") as mock_bulk:
            mock_bulk.return_value = (1, [])
            index_to_elasticsearch(MagicMock(), df, source="yfinance_file")
            mock_bulk.assert_called_once()
            actions = mock_bulk.call_args[0][1]
            self.assertEqual(actions[0]["_id"], raw_document_id("yfinance_file", "AAPL", "2024-01-02"))

        payload = {
            "ticker": "MSFT",
            "records": [
                {"date": "2024-02-01", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 100},
            ],
        }
        with patch("ingestion.ingest_api.helpers.bulk") as mock_bulk:
            mock_bulk.return_value = (1, [])
            index_api_data_to_es(MagicMock(), payload)
            mock_bulk.assert_called_once()
            actions = mock_bulk.call_args[0][1]
            self.assertEqual(actions[0]["_id"], raw_document_id("yfinance_api", "MSFT", "2024-02-01"))


if __name__ == "__main__":
    unittest.main()
