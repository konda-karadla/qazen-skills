"""Unit tests for JSON extraction / local-LLM quirks (no live provider)."""
import os

os.environ.setdefault("LLM_PROVIDER", "mock")

import pytest

from app.gateway import GatewayError, _extract_json


def test_extract_fenced_object():
    raw = 'Here you go:\n```json\n{"a": 1}\n```\n'
    assert _extract_json(raw) == {"a": 1}


def test_extract_fenced_s3_array_wraps():
    raw = """```json
[
  {"test_case_id": "TC-001"}
]
```"""
    out = _extract_json(raw, skill_id="S3")
    assert out == {"test_cases": [{"test_case_id": "TC-001"}]}


def test_bare_array_without_wrapper_raises():
    with pytest.raises(GatewayError):
        _extract_json("[1, 2]", skill_id="S1")


def test_strip_null_optional_fields():
    raw = '{"datasets":[{"dataset_id":"DS-1","test_case_id":"TC-001","data_values":{},"source":"synthetic","masking_method":null}]}'
    out = _extract_json(raw, skill_id="S4")
    assert "masking_method" not in out["datasets"][0]


def test_source_tags_inference_coerced_to_fact():
    raw = '{"test_cases":[{"source_tags":["INFERENCE","DECISION"]}]}'
    out = _extract_json(raw, skill_id="S3")
    assert out["test_cases"][0]["source_tags"] == ["FACT", "DECISION"]
