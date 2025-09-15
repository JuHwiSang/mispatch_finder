from .app.main import run_analysis, show_results

__all__ = ["run_analysis", "show_results"]

# stdlib logging defaults: attach NullHandler to prevent 'No handler' warnings
import logging
_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


