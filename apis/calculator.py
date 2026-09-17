from __future__ import annotations

import ast
import operator

from .base import APIResponse, BaseAPI


class CalculatorAPI(BaseAPI):
    name = "calculator"
    description = "Evaluates a basic arithmetic expression and returns the numeric result."
    parameters = {"expression": "A string containing a basic arithmetic expression, e.g. '2 + 2 * 3'."}

    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
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
        return APIResponse(success=True, data=result)

    def _eval(self, node: ast.AST):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in self._OPERATORS:
            return self._OPERATORS[type(node.op)](self._eval(node.left), self._eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._OPERATORS:
            return self._OPERATORS[type(node.op)](self._eval(node.operand))
        raise ValueError("Unsupported expression.")
