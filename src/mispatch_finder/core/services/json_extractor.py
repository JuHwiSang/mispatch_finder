from __future__ import annotations

import json
from typing import Optional


class JsonExtractor:
    """Domain service for extracting JSON from LLM responses.

    Handles parsing JSON blocks that may be wrapped in markdown or text.
    """

    def extract(self, text: str) -> str:
        """Extract JSON block from text.

        Args:
            text: Raw text potentially containing JSON

        Returns:
            Extracted JSON string (formatted)

        Raises:
            ValueError: If no valid JSON found
        """
        # Find JSON boundaries
        start = text.find('{')
        end = text.rfind('}')

        if start == -1 or end == -1 or end <= start:
            # No JSON found, return as-is
            return text

        # Extract and reformat JSON
        try:
            json_str = text[start:end + 1]
            parsed = json.loads(json_str)
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            # If parsing fails, return original text
            return text
