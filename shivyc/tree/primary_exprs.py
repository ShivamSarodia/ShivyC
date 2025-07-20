"""Primary expression nodes in the AST."""

import shivyc.ctypes as ctypes
import shivyc.tree.general_nodes as general_nodes
from shivyc.ctypes import ArrayCType
from shivyc.errors import CompilerError
from shivyc.il_gen import ILValue
from shivyc.tree.expr_base import _RExprNode, _LExprNode
from shivyc.tree.utils import DirectLValue


class MultiExpr(_RExprNode):
    """Expression that is two expressions joined by comma."""

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__()
        self.left = left
        self.right = right
        self.op = op

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""
        self.left.make_il(il_code, symbol_table, c)
        return self.right.make_il(il_code, symbol_table, c)


class Number(_RExprNode):
    """Expression that is just a single number."""

    def __init__(self, number):
        """Initialize node."""
        super().__init__()
        self.number = number

    def make_il(self, il_code, symbol_table, c):
        """Make code for a literal number.

        This function does not actually make any code in the IL, it just
        returns a LiteralILValue that can be used in IL code by the caller.
        """
        v = int(str(self.number))

        if ctypes.int_min <= v <= ctypes.int_max:
            il_value = ILValue(ctypes.integer)
        elif ctypes.long_min <= v <= ctypes.long_max:
            il_value = ILValue(ctypes.longint)
        else:
            err = "integer literal too large to be represented by any " \
                  "integer type"
            raise CompilerError(err, self.number.r)

        il_code.register_literal_var(il_value, v)
        return il_value


class String(_LExprNode):
    """Expression that is a string.

    chars (List(int)) - String this expression represents, as a null-terminated
    list of the ASCII representations of each character.

    """

    def __init__(self, chars):
        """Initialize Node."""
        super().__init__()
        self.chars = chars

    def _lvalue(self, il_code, symbol_table, c):
        il_value = ILValue(ArrayCType(ctypes.char, len(self.chars)))
        il_code.register_string_literal(il_value, self.chars)
        return DirectLValue(il_value)


class Identifier(_LExprNode):
    """Expression that is a single identifier."""

    def __init__(self, identifier):
        """Initialize node."""
        super().__init__()
        self.identifier = identifier

    def _lvalue(self, il_code, symbol_table, c):
        var = symbol_table.lookup_variable(self.identifier)
        return DirectLValue(var)


class ParenExpr(general_nodes.Node):
    """Expression in parentheses.

    This is implemented a bit hackily. Rather than being an LExprNode or
    RExprNode like all the other nodes, a paren expression can be either
    depending on what's inside. So for all function calls to this function,
    we simply dispatch to the expression inside.
    """

    def __init__(self, expr):
        """Initialize node."""
        super().__init__()
        self.expr = expr

    def lvalue(self, il_code, symbol_table, c):
        """Return lvalue of this expression."""
        return self.expr.lvalue(il_code, symbol_table, c)

    def make_il(self, il_code, symbol_table, c):
        """Make IL code for this expression."""
        return self.expr.make_il(il_code, symbol_table, c)

    def make_il_raw(self, il_code, symbol_table, c):
        """Make raw IL code for this expression."""
        return self.expr.make_il_raw(il_code, symbol_table, c)
