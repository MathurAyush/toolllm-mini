from __future__ import annotations

import ast
import math
import operator

from .base import APIResponse, BaseAPI


# Powers whose result would have more digits than this are refused, so an
# input such as 9**9**9 cannot tie up the process.
_MAX_POWER_DIGITS = 1000


def _power(base, exponent):
    if isinstance(base, int) and isinstance(exponent, int) and abs(base) > 1 and exponent > 0:
        if exponent * math.log10(abs(base)) > _MAX_POWER_DIGITS:
            raise ValueError("Result too large.")
    return operator.pow(base, exponent)


class CalculatorAPI(BaseAPI):
    name = "calculator"
    description = (
        "Calculates basic arithmetic math: plus, minus, times, divided by, power. "
        "Returns the numeric result."
    )
    parameters = {"expression": "A string containing a basic arithmetic expression, e.g. '2 + 2 * 3'."}
    category = "math"
    example_call = {"expression": "12 * 7 + 5"}
    example_response = 89

    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: _power,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def call(self, expression: str) -> APIResponse:
        try:
            tree = ast.parse(expression, mode="eval")
            result = self._eval(tree.body)
        except Exception as exc:
            return APIResponse(success=False, error=str(exc))
        if isinstance(result, float) and not math.isfinite(result):
            return APIResponse(success=False, error="Result is not a finite number.")
        return APIResponse(success=True, data=result)

    def _eval(self, node: ast.AST):
        # A whitelist of numeric literals and arithmetic operators: names,
        # calls and attributes are rejected, so nothing else can be run.
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in self._OPERATORS:
            return self._OPERATORS[type(node.op)](self._eval(node.left), self._eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._OPERATORS:
            return self._OPERATORS[type(node.op)](self._eval(node.operand))
        raise ValueError("Unsupported expression.")
