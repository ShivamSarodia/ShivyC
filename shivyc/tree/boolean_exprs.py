"""Boolean expression nodes in the AST."""

import shivyc.ctypes as ctypes
import shivyc.il_cmds.control as control_cmds
import shivyc.il_cmds.value as value_cmds
from shivyc.errors import CompilerError
from shivyc.il_gen import ILValue
from shivyc.tree.expr_base import _RExprNode


class _BoolAndOr(_RExprNode):
    """Base class for && and || operators."""

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__()
        self.left = left
        self.right = right
        self.op = op

    # JumpZero for &&, and JumpNotZero for ||
    jump_cmd = None

    # 1 for &&, 0 for ||
    initial_value = 1

    def make_il(self, il_code, symbol_table, c):
        # ILValue for storing the output of this boolean operation
        out = ILValue(ctypes.integer)

        # ILValue for initial value of output variable.
        init = ILValue(ctypes.integer)
        il_code.register_literal_var(init, self.initial_value)

        # ILValue for other value of output variable.
        other = ILValue(ctypes.integer)
        il_code.register_literal_var(other, 1 - self.initial_value)

        # Label which immediately precedes the line which sets out to 0 or 1.
        set_out = il_code.get_label()

        # Label which skips the line which sets out to 0 or 1.
        end = il_code.get_label()

        err = f"'{str(self.op)}' operator requires scalar operands"
        left = self.left.make_il(il_code, symbol_table, c)
        if not left.ctype.is_scalar():
            raise CompilerError(err, self.left.r)

        il_code.add(value_cmds.Set(out, init))
        il_code.add(self.jump_cmd(left, set_out))
        right = self.right.make_il(il_code, symbol_table, c)
        if not right.ctype.is_scalar():
            raise CompilerError(err, self.right.r)

        il_code.add(self.jump_cmd(right, set_out))
        il_code.add(control_cmds.Jump(end))
        il_code.add(control_cmds.Label(set_out))
        il_code.add(value_cmds.Set(out, other))
        il_code.add(control_cmds.Label(end))
        return out


class BoolAnd(_BoolAndOr):
    """Expression that performs boolean and of two values."""

    jump_cmd = control_cmds.JumpZero
    initial_value = 1


class BoolOr(_BoolAndOr):
    """Expression that performs boolean or of two values."""

    jump_cmd = control_cmds.JumpNotZero
    initial_value = 0


class BoolNot(_RExprNode):
    """Boolean not."""

    def __init__(self, expr):
        """Initialize node."""
        super().__init__()
        self.expr = expr

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""

        expr = self.expr.make_il(il_code, symbol_table, c)
        if not expr.ctype.is_scalar():
            err = "'!' operator requires scalar operand"
            raise CompilerError(err, self.r)

        # ILValue for storing the output
        out = ILValue(ctypes.integer)

        # ILValue for zero.
        zero = ILValue(ctypes.integer)
        il_code.register_literal_var(zero, "0")

        # ILValue for one.
        one = ILValue(ctypes.integer)
        il_code.register_literal_var(one, "1")

        # Label which skips the line which sets out to 0.
        end = il_code.get_label()

        il_code.add(value_cmds.Set(out, one))
        il_code.add(control_cmds.JumpZero(expr, end))
        il_code.add(value_cmds.Set(out, zero))
        il_code.add(control_cmds.Label(end))

        return out
