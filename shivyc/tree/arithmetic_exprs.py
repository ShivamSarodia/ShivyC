"""Arithmetic expression nodes in the AST."""

import shivyc.ctypes as ctypes
import shivyc.il_cmds.math as math_cmds
from shivyc.errors import CompilerError
from shivyc.il_gen import ILValue
from shivyc.tree.expr_base import _RExprNode
from shivyc.tree.utils import arith_convert, get_size, shift_into_range


class _ArithBinOp(_RExprNode):
    """Base class for some binary operators.

    Binary operators like +, -, ==, etc. are similar in many respects. They
    convert their arithmetic arguments, etc. This is a base class for
    nodes of those types of operators.
    """

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__()
        self.left = left
        self.right = right
        self.op = op

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""

        left = self.left.make_il(il_code, symbol_table, c)
        right = self.right.make_il(il_code, symbol_table, c)

        if self._check_type(left, right):
            left, right = arith_convert(left, right, il_code)

            if left.literal and right.literal:
                # If NotImplementedError is raised, continue with execution.
                try:
                    val = self._arith_const(
                        shift_into_range(left.literal.val, left.ctype),
                        shift_into_range(right.literal.val, right.ctype),
                        left.ctype)
                    out = ILValue(left.ctype)
                    il_code.register_literal_var(out, val)
                    return out

                except NotImplementedError:
                    pass

            return self._arith(left, right, il_code)

        else:
            return self._nonarith(left, right, il_code)

    default_il_cmd = None

    def _check_type(self, left, right):
        """Returns True if both arguments has arithmetic type.

        left - ILValue for left operand
        right - ILValue for right operand
        """
        return left.ctype.is_arith() and right.ctype.is_arith()

    def _arith(self, left, right, il_code):
        """Return the result of this operation on given arithmetic operands.

        Promotions and conversions are done by caller, so the implementation of
        this function need not convert operands.

        A default implementation is provided, but this can be overriden by
        derived classes.

        left - ILValue for left operand
        right - ILValue for right operand
        """
        out = ILValue(left.ctype)
        il_code.add(self.default_il_cmd(out, left, right))
        return out

    def _arith_const(self, left, right, ctype):
        """Return the result on compile-time constant operands.

        For example, an expression like `4 + 3` can be evaluated at compile
        time without emitting any IL code. This doubles as both an
        implementation of constant expressions in C and as a compiler
        optimization.

        Promotions and conversions are done by caller, so the implementation of
        this function need not convert operands. Also, the `left` and
        `right` values are guaranteed to be in the range of representable
        values for the given ctype.

        If this function raises NotImplementedError, the caller will use
        the _arith function on given operands instead.

        left_val - the NUMERICAL value of the left operand
        right_val - the NUMERICAL value of the right operand.
        """
        raise NotImplementedError

    def _nonarith(self, left, right, il_code):
        """Return the result of this operation on given nonarithmetic operands.

        left - ILValue for left operand
        right - ILValue for right operand
        """
        raise NotImplementedError


class Plus(_ArithBinOp):
    """Expression that is sum of two expressions.

    left - Expression on left side
    right - Expression on right side
    op (Token) - Plus operator token
    """

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__(left, right, op)

    default_il_cmd = math_cmds.Add

    def _arith_const(self, left, right, ctype):
        return shift_into_range(left + right, ctype)

    def _nonarith(self, left, right, il_code):
        """Make addition code if either operand is non-arithmetic type."""

        # One operand should be pointer to complete object type, and the
        # other should be any integer type.
        if left.ctype.is_pointer() and right.ctype.is_integral():
            arith, pointer = right, left
        elif right.ctype.is_pointer() and left.ctype.is_integral():
            arith, pointer = left, right
        else:
            err = "invalid operand types for addition"
            raise CompilerError(err, self.op.r)

        if not pointer.ctype.arg.is_complete():
            err = "invalid arithmetic on pointer to incomplete type"
            raise CompilerError(err, self.op.r)

        # Multiply by size of objects
        out = ILValue(pointer.ctype)
        shift = get_size(pointer.ctype.arg, arith, il_code)
        il_code.add(math_cmds.Add(out, pointer, shift))
        return out


class Minus(_ArithBinOp):
    """Expression that is the difference of two expressions.

    left - Expression on left side
    right - Expression on right side
    op (Token) - Plus operator token
    """

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__(left, right, op)

    default_il_cmd = math_cmds.Subtr

    def _arith_const(self, left, right, ctype):
        return shift_into_range(left - right, ctype)

    def _nonarith(self, left, right, il_code):
        """Make subtraction code if both operands are non-arithmetic type."""

        # TODO: this isn't quite right when we allow qualifiers
        if (left.ctype.is_pointer() and right.ctype.is_pointer()
             and left.ctype.compatible(right.ctype)):

            if (not left.ctype.arg.is_complete()
                  or not right.ctype.arg.is_complete()):
                err = "invalid arithmetic on pointers to incomplete types"
                raise CompilerError(err, self.op.r)

            # Get raw difference in pointer values
            raw = ILValue(ctypes.longint)
            il_code.add(math_cmds.Subtr(raw, left, right))

            # Divide by size of object
            out = ILValue(ctypes.longint)
            size = ILValue(ctypes.longint)
            il_code.register_literal_var(size, str(left.ctype.arg.size))
            il_code.add(math_cmds.Div(out, raw, size))

            return out

        # Left operand is pointer to complete object type, and right operand
        # is integer.
        elif left.ctype.is_pointer() and right.ctype.is_integral():
            if not left.ctype.arg.is_complete():
                err = "invalid arithmetic on pointer to incomplete type"
                raise CompilerError(err, self.op.r)

            out = ILValue(left.ctype)
            shift = get_size(left.ctype.arg, right, il_code)
            il_code.add(math_cmds.Subtr(out, left, shift))
            return out

        else:
            descrip = "invalid operand types for subtraction"
            raise CompilerError(descrip, self.op.r)


class Mult(_ArithBinOp):
    """Expression that is product of two expressions."""

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__(left, right, op)

    default_il_cmd = math_cmds.Mult

    def _arith_const(self, left, right, ctype):
        return shift_into_range(left * right, ctype)

    def _nonarith(self, left, right, il_code):
        err = "invalid operand types for multiplication"
        raise CompilerError(err, self.op.r)


class _IntBinOp(_ArithBinOp):
    """Base class for operations that works with integral type operands."""

    def _check_type(self, left, right):
        """Performs additional type check for operands.

        left - ILValue for left operand
        right - ILValue for right operand
        """
        return left.ctype.is_integral() and right.ctype.is_integral()


class Div(_ArithBinOp):
    """Expression that is quotient of two expressions."""

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__(left, right, op)

    default_il_cmd = math_cmds.Div

    def _arith_const(self, left, right, ctype):
        return shift_into_range(int(left / right), ctype)

    def _nonarith(self, left, right, il_code):
        err = "invalid operand types for division"
        raise CompilerError(err, self.op.r)


class Mod(_IntBinOp):
    """Expression that is modulus of two expressions."""

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__(left, right, op)

    default_il_cmd = math_cmds.Mod

    def _nonarith(self, left, right, il_code):
        err = "invalid operand types for modulus"
        raise CompilerError(err, self.op.r)


class _BitShift(_IntBinOp):
    """Represents a `<<` and `>>` bitwise shift operators.
    Each of operands must have integer type.
    """

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__(left, right, op)

    def _nonarith(self, left, right, il_code):
        err = "invalid operand types for bitwise shift"
        raise CompilerError(err, self.op.r)


class RBitShift(_BitShift):
    """Represent a `>>` operator."""

    default_il_cmd = math_cmds.RBitShift


class LBitShift(_BitShift):
    """Represent a `<<` operator."""

    default_il_cmd = math_cmds.LBitShift
