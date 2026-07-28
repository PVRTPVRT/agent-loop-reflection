"""Responses API provider with a strict V2 evaluation-suite schema."""

from __future__ import annotations

from agentloop.structured_llm import StructuredOpenAIProvider

SCALARS = [
    {"type": "null"},
    {"type": "boolean"},
    {"type": "integer"},
    {"type": "number"},
    {"type": "string"},
]

JSON_VALUE_V2_SCHEMA = {
    "anyOf": [
        *SCALARS,
        {
            "type": "array",
            "items": {
                "anyOf": [
                    *SCALARS,
                    {"type": "array", "items": {"anyOf": SCALARS}},
                ]
            },
        },
    ]
}

EVALUATION_SUITE_V2_SCHEMA = {
    "type": "object",
    "properties": {
        "function_name": {"type": "string", "minLength": 1},
        "test_cases": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "args": {
                        "type": "array",
                        "items": JSON_VALUE_V2_SCHEMA,
                    },
                    "expected": JSON_VALUE_V2_SCHEMA,
                    "expected_exception": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ]
                    },
                    "description": {"type": "string"},
                },
                "required": [
                    "args",
                    "expected",
                    "expected_exception",
                    "description",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["function_name", "test_cases"],
    "additionalProperties": False,
}


class StrictV2OpenAIProvider(StructuredOpenAIProvider):
    """Apply the V2 suite schema to Tester requests."""

    def generate(self, request):
        if request.metadata.get("agent") != "tester":
            return super().generate(request)

        original_create = self._client.responses.create

        def create_with_v2_schema(**kwargs):
            kwargs["text"]["format"]["schema"] = EVALUATION_SUITE_V2_SCHEMA
            kwargs["text"]["format"]["name"] = "evaluation_suite_v2"
            return original_create(**kwargs)

        self._client.responses.create = create_with_v2_schema
        try:
            return super().generate(request)
        finally:
            self._client.responses.create = original_create
