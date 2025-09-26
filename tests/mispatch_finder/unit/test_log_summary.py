import json
from pathlib import Path

from mispatch_finder.shared.log_summary import summarize_logs


def _make_log_line(message: str, payload: dict) -> str:
    return json.dumps({"message": message, "payload": payload})


def test_log_summary_uses_latest_fields_current_then_patch(tmp_path: Path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # File 1: current_risk present (new flat schema)
    data1 = {
        "current_risk": "high",
        "patch_risk": "good",
    }
    (logs_dir / "GHSA-ONE.jsonl").write_text(
        "\n".join(
            [
                _make_log_line(
                    "final_result",
                    {"type": "final_result", "result": {"raw_text": json.dumps(data1)}},
                ),
            ]
        ),
        encoding="utf-8",
    )

    # File 2: only patch_risk present (new flat schema)
    data2 = {
        "patch_risk": "good",
    }
    (logs_dir / "GHSA-TWO.jsonl").write_text(
        "\n".join(
            [
                _make_log_line(
                    "final_result",
                    {"type": "final_result", "result": {"raw_text": json.dumps(data2)}},
                ),
            ]
        ),
        encoding="utf-8",
    )

    summaries = summarize_logs(logs_dir, verbose=False)
    assert summaries["GHSA-ONE"].current_risk == "high"
    assert summaries["GHSA-TWO"].patch_risk == "good"


