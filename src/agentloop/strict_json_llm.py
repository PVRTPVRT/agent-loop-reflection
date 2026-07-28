"""OpenAI provider using strict, fully typed JSON schemas."""

from __future__ import annotations

from agentloop.structured_llm import StructuredOpenAIProvider

SCALAR_SCHEMA = {
    "anyOf": [
        {"type": "null"},
        {"type": "boolean"},
        {"type": "integer"},
        {"type": "number"},
        {"type": "string"},
    ]
}

JSON_VALUE_SCHEMA = {
    "anyOf": [
        *SCALAR_SCHEMA["anyOf"],
        {
            "type": "array",
            "items": {
                "anyOf": [
                    *SCALAR_SCHEMA["anyOf"],
                    {"type": "array", "items": SCALAR_SCHEMA},
                ]
            },
        },
    ]
}

STRICT_TEST_SUITE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "function_name": {"type": "string", "minLength": 1},
        "test_cases": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "args": {"type": "array", "items": JSON_VALUE_SCHEMA},
                    "expected": JSON_VALUE_SCHEMA,
                    "description": {"type": "string"},
                },
                "required": ["args", "expected", "description"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["function_name", "test_cases"],
    "additionalProperties": False,
}


class StrictJSONOpenAIProvider(StructuredOpenAIProvider):
    """Replace the Tester schema with one accepted by strict validation."""

    def generate(self, request):
        if request.metadata.get("agent") != "tester":
            return super().generate(request)

        original_create = self._client.responses.create

        def create_with_strict_schema(**kwargs):
            kwargs["text"]["format"]["schema"] = STRICT_TEST_SUITE_JSON_SCHEMA
            return original_create(**kwargs)

        self._client.responses.create = create_with_strict_schema
        try:
            return super().generate(request)
        finally:
            self._client.responses.create = original_create
