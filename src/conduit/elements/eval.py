from .. import PipelineElement
from typing import Any, Generator, Iterator
from ..utils import get_functions
import ast
import operator

# Safe operations for expression evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.LShift: operator.lshift,
    ast.RShift: operator.rshift,
    ast.BitOr: operator.or_,
    ast.BitXor: operator.xor,
    ast.BitAnd: operator.and_,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
    ast.In: lambda x, y: x in y,
    ast.NotIn: lambda x, y: x not in y,
    ast.And: lambda x, y: x and y,
    ast.Or: lambda x, y: x or y,
    ast.Not: lambda x: not x,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Invert: operator.invert,
}

class SafeExpressionEvaluator:
    """Safe expression evaluator using AST parsing"""
    
    def __init__(self, allowed_names: set = None):
        self.allowed_names = allowed_names or set()
    
    def evaluate(self, expression: str, context: dict) -> Any:
        """Safely evaluate a Python expression"""
        try:
            node = ast.parse(expression, mode='eval')
            return self._eval_node(node.body, context)
        except Exception as e:
            raise ValueError(f"Expression evaluation failed: {e}")
    
    def _eval_node(self, node, context):
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Num):  # Python < 3.8
            return node.n
        elif isinstance(node, ast.Str):  # Python < 3.8
            return node.s
        elif isinstance(node, ast.NameConstant):  # Python < 3.8
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in context:
                return context[node.id]
            else:
                raise ValueError(f"Name '{node.id}' is not defined or not allowed")
        elif isinstance(node, ast.Attribute):
            obj = self._eval_node(node.value, context)
            return getattr(obj, node.attr)
        elif isinstance(node, ast.Subscript):
            obj = self._eval_node(node.value, context)
            key = self._eval_node(node.slice, context)
            return obj[key]
        elif isinstance(node, ast.Index):  # Python < 3.9
            return self._eval_node(node.value, context)
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)
            op_func = SAFE_OPERATORS.get(type(node.op))
            if op_func:
                return op_func(left, right)
            else:
                raise ValueError(f"Operator {type(node.op).__name__} not allowed")
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, context)
            op_func = SAFE_OPERATORS.get(type(node.op))
            if op_func:
                return op_func(operand)
            else:
                raise ValueError(f"Unary operator {type(node.op).__name__} not allowed")
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            result = True
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context)
                op_func = SAFE_OPERATORS.get(type(op))
                if op_func:
                    result = result and op_func(left, right)
                    left = right
                else:
                    raise ValueError(f"Comparison operator {type(op).__name__} not allowed")
            return result
        elif isinstance(node, ast.BoolOp):
            op_func = SAFE_OPERATORS.get(type(node.op))
            if not op_func:
                raise ValueError(f"Boolean operator {type(node.op).__name__} not allowed")
            
            values = [self._eval_node(value, context) for value in node.values]
            result = values[0]
            for value in values[1:]:
                result = op_func(result, value)
            return result
        elif isinstance(node, ast.List):
            return [self._eval_node(elem, context) for elem in node.elts]
        elif isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elem, context) for elem in node.elts)
        elif isinstance(node, ast.Dict):
            keys = [self._eval_node(key, context) for key in node.keys]
            values = [self._eval_node(value, context) for value in node.values]
            return dict(zip(keys, values))
        else:
            raise ValueError(f"Node type {type(node).__name__} not allowed")

class Eval(PipelineElement):
    def __init__(self, expression: str):
        self.expression = expression
        self.evaluator = SafeExpressionEvaluator()

    def process(self, input: Iterator[Any]) -> Generator[Any, None, None]:
        for i in input:
            context = get_functions()
            context["input"] = i
            result = self.evaluator.evaluate(self.expression, context)
            yield result