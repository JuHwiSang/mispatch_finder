# Public API will be exposed via app.api module (future implementation)
# For now, use CLI via: python -m mispatch_finder.app.cli

__all__ = []

# stdlib logging defaults: attach NullHandler to prevent 'No handler' warnings
import logging
_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


