"""Assignment expression nodes in the AST."""

import shivyc.il_cmds.math as math_cmds
from shivyc.errors import CompilerError
from shivyc.il_gen import ILValue
from shivyc.tree.expr_base import _RExprNode
from shivyc.tree.utils import arith_convert, get_size


class Equals(_RExprNode):
    """Expression that is an assignment."""

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__()
        self.left = left
        self.right = right
        self.op = op

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""
        right = self.right.make_il(il_code, symbol_table, c)
        lvalue = self.left.lvalue(il_code, symbol_table, c)

        if lvalue and lvalue.modable():
            return lvalue.set_to(right, il_code, self.op.r)
        else:
            err = "expression on left of '=' is not assignable"
            raise CompilerError(err, self.left.r)


class _CompoundPlusMinus(_RExprNode):
    """Expression that is += or -=."""

    # Command to execute to change the value of the variable.  Use
    # math_cmds.Add for +=, math_cmds.Subtr for -=, etc.
    command = None
    # True if this command should accept a pointer as left operand. Set this to
    # True for += and -=, and false for all others.
    accept_pointer = False

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__()
        self.left = left
        self.right = right
        self.op = op

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""
        right = self.right.make_il(il_code, symbol_table, c)
        lvalue = self.left.lvalue(il_code, symbol_table, c)
        if not lvalue or not lvalue.modable():
            err = f"expression on left of '{str(self.op)}' is not assignable"
            raise CompilerError(err, self.left.r)

        if (lvalue.ctype().is_pointer()
            and right.ctype.is_integral()
             and self.accept_pointer):

            if not lvalue.ctype().arg.is_complete():
                err = "invalid arithmetic on pointer to incomplete type"
                raise CompilerError(err, self.op.r)

            # Because of caching requirement of make_il and lvalue functions,
            # we know this call won't regenerate code for the left expression
            # beyond just what's needed to get the value stored at the lvalue.
            # This is important in cases like ``*func() += 10`` where func()
            # may have side effects if called twice.
            left = self.left.make_il(il_code, symbol_table, c)

            out = ILValue(left.ctype)
            shift = get_size(left.ctype.arg, right, il_code)

            il_code.add(self.command(out, left, shift))
            lvalue.set_to(out, il_code, self.op.r)
            return out

        elif lvalue.ctype().is_arith() and right.ctype.is_arith():
            left = self.left.make_il(il_code, symbol_table, c)
            out = ILValue(left.ctype)

            left, right = arith_convert(left, right, il_code)
            il_code.add(self.command(out, left, right))
            lvalue.set_to(out, il_code, self.op.r)
            return out

        else:
            err = f"invalid types for '{str(self.op)}' operator"
            raise CompilerError(err, self.op.r)


class PlusEquals(_CompoundPlusMinus):
    """Expression that is +=."""

    command = math_cmds.Add
    accept_pointer = True


class MinusEquals(_CompoundPlusMinus):
    """Expression that is -=."""

    command = math_cmds.Subtr
    accept_pointer = True


class StarEquals(_CompoundPlusMinus):
    """Expression that is *=."""

    command = math_cmds.Mult
    accept_pointer = False


class DivEquals(_CompoundPlusMinus):
    """Expression that is /=."""

    command = math_cmds.Div
    accept_pointer = False


class ModEquals(_CompoundPlusMinus):
    """Expression that is %=."""

    command = math_cmds.Mod
    accept_pointer = False
