from pathlib import Path


def test_reusable_code_is_packaged_under_src():
    package = Path("src/financial_data_lake")

    assert (package / "__init__.py").is_file()
    assert (package / "config/settings.py").is_file()
    assert (package / "ingestion/ingest_file.py").is_file()
    assert (package / "ingestion/ingest_api.py").is_file()
    assert (package / "transformation/staging/transform_staging.py").is_file()
    assert (package / "transformation/curated/transform_curated.py").is_file()
