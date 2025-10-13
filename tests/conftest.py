import sys
from pathlib import Path
import pytest
from helpers import mark_by_dir

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@pytest.fixture(autouse=True)
def _ensure_src_on_syspath():
    # Add project src/ to sys.path for src-layout imports
    root = Path(__file__).resolve().parents[1]
    src_path = root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    yield


TESTS = Path(__file__).parent

def pytest_collection_modifyitems(config, items):
    # Mark tests by directory structure
    mark_by_dir(items, TESTS / "mispatch_finder" / "core", pytest.mark.unit)
    mark_by_dir(items, TESTS / "mispatch_finder" / "infra", pytest.mark.integration)
    mark_by_dir(items, TESTS / "mispatch_finder" / "app", pytest.mark.e2e)
    mark_by_dir(items, TESTS / "mispatch_finder" / "shared", pytest.mark.unit)