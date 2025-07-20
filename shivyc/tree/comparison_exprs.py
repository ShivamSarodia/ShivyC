"""Comparison and equality expression nodes in the AST."""

import shivyc.ctypes as ctypes
import shivyc.il_cmds.compare as compare_cmds
from shivyc.errors import CompilerError
from shivyc.il_gen import ILValue
from shivyc.tree.arithmetic_exprs import _ArithBinOp
from shivyc.tree.utils import set_type, check_cast, report_err


class _Equality(_ArithBinOp):
    """Base class for == and != nodes."""

    eq_il_cmd = None

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__(left, right, op)

    def _arith(self, left, right, il_code):
        """Check equality of arithmetic expressions."""
        out = ILValue(ctypes.integer)
        il_code.add(self.eq_il_cmd(out, left, right))
        return out

    def _nonarith(self, left, right, il_code):
        """Check equality of non-arithmetic expressions."""

        # If either operand is a null pointer constant, cast it to the
        # other's pointer type.
        if (left.ctype.is_pointer()
             and getattr(right.literal, "val", None) == 0):
            right = set_type(right, left.ctype, il_code)
        elif (right.ctype.is_pointer()
              and getattr(left.literal, "val", None) == 0):
            left = set_type(left, right.ctype, il_code)

        # If both operands are not pointer types, quit now
        if not left.ctype.is_pointer() or not right.ctype.is_pointer():
            with report_err():
                err = "comparison between incomparable types"
                raise CompilerError(err, self.op.r)

        # If one side is pointer to void, cast the other to same.
        elif left.ctype.arg.is_void():
            check_cast(right, left.ctype, self.op.r)
            right = set_type(right, left.ctype, il_code)
        elif right.ctype.arg.is_void():
            check_cast(left, right.ctype, self.op.r)
            left = set_type(left, right.ctype, il_code)

        # If both types are still incompatible, warn!
        elif not left.ctype.compatible(right.ctype):
            with report_err():
                err = "comparison between distinct pointer types"
                raise CompilerError(err, self.op.r)

        # Now, we can do comparison
        out = ILValue(ctypes.integer)
        il_code.add(self.eq_il_cmd(out, left, right))
        return out


class Equality(_Equality):
    """Expression that checks equality of two expressions."""

    eq_il_cmd = compare_cmds.EqualCmp


class Inequality(_Equality):
    """Expression that checks inequality of two expressions."""

    eq_il_cmd = compare_cmds.NotEqualCmp


class _Relational(_ArithBinOp):
    """Base class for <, <=, >, and >= nodes."""

    comp_cmd = None

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__(left, right, op)

    def _arith(self, left, right, il_code):
        """Compare arithmetic expressions."""
        out = ILValue(ctypes.integer)
        il_code.add(self.comp_cmd(out, left, right))
        return out

    def _nonarith(self, left, right, il_code):
        """Compare non-arithmetic expressions."""

        if not left.ctype.is_pointer() or not right.ctype.is_pointer():
            err = "comparison between incomparable types"
            raise CompilerError(err, self.op.r)
        elif not left.ctype.compatible(right.ctype):
            err = "comparison between distinct pointer types"
            raise CompilerError(err, self.op.r)

        out = ILValue(ctypes.integer)
        il_code.add(self.comp_cmd(out, left, right))
        return out


class LessThan(_Relational):
    """Less than comparison expression."""
    comp_cmd = compare_cmds.LessCmp


class GreaterThan(_Relational):
    """Greater than comparison expression."""
    comp_cmd = compare_cmds.GreaterCmp


class LessThanOrEq(_Relational):
    """Less than or equal comparison expression."""
    comp_cmd = compare_cmds.LessOrEqCmp


class GreaterThanOrEq(_Relational):
    """Greater than or equal comparison expression."""
    comp_cmd = compare_cmds.GreaterOrEqCmp
