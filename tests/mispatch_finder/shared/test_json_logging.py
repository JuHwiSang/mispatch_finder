import json
import logging
from pathlib import Path

from mispatch_finder.shared.json_logging import build_json_console_handler, build_json_file_handler


def test_build_json_console_handler():
    handler = build_json_console_handler(level=logging.INFO)
    
    assert handler is not None
    assert handler.level == logging.INFO
    assert handler.formatter is not None


def test_build_json_file_handler(tmp_path):
    log_file = tmp_path / "test.jsonl"
    
    handler = build_json_file_handler(log_file, level=logging.DEBUG)
    
    assert handler is not None
    assert handler.level == logging.DEBUG
    assert handler.formatter is not None


def test_json_logging_format(tmp_path):
    """Test that logs are written in JSON format."""
    log_file = tmp_path / "test.jsonl"
    
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    
    handler = build_json_file_handler(log_file, level=logging.INFO)
    logger.addHandler(handler)
    
    # Write a log message
    logger.info("test_message", extra={"payload": {"type": "test", "data": "value"}})
    
    # Flush and close handler
    handler.flush()
    handler.close()
    
    # Read and verify JSON format
    content = log_file.read_text(encoding="utf-8")
    lines = [line for line in content.split("\n") if line.strip()]
    
    assert len(lines) > 0
    
    # Parse first line as JSON
    log_entry = json.loads(lines[0])
    assert "message" in log_entry
    assert log_entry["message"] == "test_message"


def test_json_logging_with_payload(tmp_path):
    """Test that payload is included in JSON logs."""
    log_file = tmp_path / "test_payload.jsonl"
    
    logger = logging.getLogger("test_payload_logger")
    logger.setLevel(logging.INFO)
    
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    
    handler = build_json_file_handler(log_file, level=logging.INFO)
    logger.addHandler(handler)
    
    logger.info("with_payload", extra={
        "payload": {
            "type": "custom_event",
            "ghsa": "GHSA-TEST",
            "value": 123,
        }
    })
    
    handler.flush()
    handler.close()
    
    content = log_file.read_text(encoding="utf-8")
    log_entry = json.loads(content.strip())
    
    assert "payload" in log_entry
    assert log_entry["payload"]["type"] == "custom_event"
    assert log_entry["payload"]["ghsa"] == "GHSA-TEST"
    assert log_entry["payload"]["value"] == 123

