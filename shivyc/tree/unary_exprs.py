"""Unary expression nodes in the AST."""

import shivyc.ctypes as ctypes
import shivyc.il_cmds.math as math_cmds
import shivyc.il_cmds.value as value_cmds
from shivyc.errors import CompilerError
from shivyc.il_gen import ILValue
from shivyc.tree.expr_base import _RExprNode
from shivyc.tree.utils import set_type, shift_into_range


class _IncrDecr(_RExprNode):
    """Base class for prefix/postfix increment/decrement operators."""

    def __init__(self, expr):
        """Initialize node."""
        super().__init__()
        self.expr = expr

    descrip = None
    cmd = None
    return_new = None

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""
        lval = self.expr.lvalue(il_code, symbol_table, c)

        if not lval or not lval.modable():
            err = f"operand of {self.descrip} operator not a modifiable lvalue"
            raise CompilerError(err, self.expr.r)

        val = self.expr.make_il(il_code, symbol_table, c)
        one = ILValue(val.ctype)
        if val.ctype.is_arith():
            il_code.register_literal_var(one, 1)
        elif val.ctype.is_pointer() and val.ctype.arg.is_complete():
            il_code.register_literal_var(one, val.ctype.arg.size)
        elif val.ctype.is_pointer():
            # technically, this message is not quite right because for
            # non-object types, a type can be neither complete nor incomplete
            err = "invalid arithmetic on pointer to incomplete type"
            raise CompilerError(err, self.expr.r)
        else:
            err = f"invalid type for {self.descrip} operator"
            raise CompilerError(err, self.expr.r)

        new_val = ILValue(val.ctype)

        if self.return_new:
            il_code.add(self.cmd(new_val, val, one))
            lval.set_to(new_val, il_code, self.expr.r)
            return new_val
        else:
            old_val = ILValue(val.ctype)
            il_code.add(value_cmds.Set(old_val, val))
            il_code.add(self.cmd(new_val, val, one))
            lval.set_to(new_val, il_code, self.expr.r)
            return old_val


class PreIncr(_IncrDecr):
    """Prefix increment."""

    descrip = "increment"
    cmd = math_cmds.Add
    return_new = True


class PostIncr(_IncrDecr):
    """Postfix increment."""

    descrip = "increment"
    cmd = math_cmds.Add
    return_new = False


class PreDecr(_IncrDecr):
    """Prefix decrement."""

    descrip = "decrement"
    cmd = math_cmds.Subtr
    return_new = True


class PostDecr(_IncrDecr):
    """Postfix decrement."""

    descrip = "decrement"
    cmd = math_cmds.Subtr
    return_new = False


class _ArithUnOp(_RExprNode):
    """Base class for unary plus, minus, and bit-complement."""

    descrip = None
    opnd_descrip = "arithmetic"
    cmd = None

    def __init__(self, expr):
        """Initialize node."""
        super().__init__()
        self.expr = expr

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""
        expr = self.expr.make_il(il_code, symbol_table, c)
        if not self._check_type(expr):
            err = f"{self.descrip} requires {self.opnd_descrip} type operand"
            raise CompilerError(err, self.expr.r)
        # perform integer promotion
        if expr.ctype.size < 4:
            expr = set_type(expr, ctypes.integer, il_code)
        if self.cmd:
            out = ILValue(expr.ctype)
            # perform constant folding
            if expr.literal:
                val = self._arith_const(expr.literal.val, expr.ctype)
                val = shift_into_range(val, expr.ctype)
                il_code.register_literal_var(out, val)
            else:
                il_code.add(self.cmd(out, expr))
            return out
        return expr

    def _check_type(self, expr):
        """Returns True if the argument has arithmetic type.

        This default implementation can be overriden by derived classes if a
        different type is required.

        """
        return expr.ctype.is_arith()

    def _arith_const(self, expr, ctype):
        """Return the result on compile-time constant operand."""
        raise NotImplementedError


class UnaryPlus(_ArithUnOp):
    """Positive."""

    descrip = "unary plus"


class UnaryMinus(_ArithUnOp):
    """Negative."""

    descrip = "unary minus"
    cmd = math_cmds.Neg

    def _arith_const(self, expr, ctype):
        return -shift_into_range(expr, ctype)


class Compl(_ArithUnOp):
    """Logical bitwise negative."""

    descrip = "bit-complement"
    opnd_descrip = "integral"
    cmd = math_cmds.Not

    def _check_type(self, expr):
        return expr.ctype.is_integral()

    def _arith_const(self, expr, ctype):
        return ~shift_into_range(expr, ctype)
