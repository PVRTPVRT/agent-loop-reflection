"""Parsers for structured model outputs."""

from __future__ import annotations

import ast
import json
import re

from pydantic import ValidationError

from agentloop.models import TestSuite


class ModelOutputError(ValueError):
    """Raised when model output does not satisfy the required contract."""


def extract_json_object(text: str) -> dict:
    candidate = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ModelOutputError(f"模型未返回合法 JSON：{exc.msg}") from exc
    if not isinstance(value, dict):
        raise ModelOutputError("模型 JSON 顶层必须是对象")
    return value


def parse_test_suite(text: str) -> TestSuite:
    try:
        return TestSuite.model_validate(extract_json_object(text))
    except ValidationError as exc:
        raise ModelOutputError(f"测试套件结构无效：{exc}") from exc


def extract_python_code(text: str) -> str:
    candidate = text.strip()
    fenced = re.search(r"```(?:python)?\s*(.*?)\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
    if not candidate:
        raise ModelOutputError("模型未返回 Python 代码")
    try:
        ast.parse(candidate)
    except SyntaxError as exc:
        location = f"第 {exc.lineno} 行" if exc.lineno else "未知位置"
        raise ModelOutputError(f"Python 语法错误（{location}）：{exc.msg}") from exc
    return candidate
