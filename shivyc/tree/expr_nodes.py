"""Nodes in the AST which represent expression values."""

import shivyc.ctypes as ctypes
import shivyc.tree.nodes as nodes
import shivyc.il_cmds.compare as compare_cmds
import shivyc.il_cmds.control as control_cmds
import shivyc.il_cmds.math as math_cmds
import shivyc.il_cmds.value as value_cmds

from shivyc.ctypes import ArrayCType, PointerCType
from shivyc.errors import CompilerError
from shivyc.il_gen import ILValue
from shivyc.tree.nodes import Declaration
from shivyc.tree.utils import (IndirectLValue, DirectLValue, RelativeLValue,
                               check_cast, set_type, arith_convert,
                               get_size, report_err, shift_into_range)


class _ExprNode(nodes.Node):
    """Base class for representing expression nodes in the AST.

    There are two types of expression nodes, RExprNode and LExprNode.
    An expression node which can be used as an lvalue (that is, an expression
    node which can be the argument of an address-of operator) derives from
    LExprNode. Expression nodes which cannot be used as lvalues derive from
    RExprNode.
    """
    def __init__(self):
        """Initialize this ExprNode."""
        super().__init__()

    def make_il(self, il_code, symbol_table, c):
        """Generate IL code for this node and returns ILValue.

        Note that a RExprNode-derived node can never return an ILValue of
        function or array type because these must decay to addresses,
        and because an RExprNode does not represent an lvalue, no address
        can exist.

        il_code - ILCode object to add generated code to.
        symbol_table - Symbol table for current node.
        c - Context for current node, as above. This function should not
        modify this object.
        return - An ILValue representing the result of this computation.
        """
        raise NotImplementedError

    def make_il_raw(self, il_code, symbol_table, c):
        """As above, but do not decay the result."""
        raise NotImplementedError

    def lvalue(self, il_code, symbol_table, c):
        """Return the LValue representing this node.

        If this node has no LValue representation, return None.
        """
        raise NotImplementedError


class _RExprNode(nodes.Node):
    """Base class for representing an rvalue expression node in the AST.

    An RExprNode-derived node implements only the _make_il function.
    """
    def __init__(self):  # noqa D102
        nodes.Node.__init__(self)
        self._cache_raw_ilvalue = None

    def make_il(self, il_code, symbol_table, c):  # noqa D102
        raise NotImplementedError

    def make_il_raw(self, il_code, symbol_table, c):  # noqa D102
        return self.make_il(il_code, symbol_table, c)

    def lvalue(self, il_code, symbol_table, c):  # noqa D102
        return None


class _LExprNode(nodes.Node):
    """Base class for representing an lvalue expression node in the AST.

    An LExprNode-derived node implements only the _lvalue function. This
    function returns an LValue object representing this node. The
    implementation of this class automatically sets up the appropriate
    make_il function which calls the lvalue implementation.

    Note that calling both make_il and make_il_raw for a single node may
    generate unnecessary or repeated code!
    """

    def __init__(self):  # noqa D102
        super().__init__()
        self._cache_lvalue = None

    def make_il(self, il_code, symbol_table, c):  # noqa D102
        lvalue = self.lvalue(il_code, symbol_table, c)

        # Decay array
        if lvalue.ctype().is_array():
            addr = lvalue.addr(il_code)
            return set_type(addr, PointerCType(lvalue.ctype().el), il_code)

        # Decay function
        elif lvalue.ctype().is_function():
            return lvalue.addr(il_code)

        # Nothing to decay
        else:
            return lvalue.val(il_code)

    def make_il_raw(self, il_code, symbol_table, c):  # noqa D102
        return self.lvalue(il_code, symbol_table, c).val(il_code)

    def lvalue(self, il_code, symbol_table, c):
        """Return an LValue object representing this node."""
        if not self._cache_lvalue:
            self._cache_lvalue = self._lvalue(il_code, symbol_table, c)
        return self._cache_lvalue

    def _lvalue(self, il_code, symbol_table, c):
        """Return an LValue object representing this node.

        Do not call this function directly, because it does not cache the
        result. Multiple calls to this function may generate multiple error
        messages or output repeated code to il_code.
        """
        raise NotImplementedError


class MultiExpr(_RExprNode):
    """Expression that is two expressions joined by comma."""

    def __init__(self, left, right, op):
        """Initialize node."""
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


class ParenExpr(nodes.Node):
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

            if (not left.ctype.arg.is_complete() or
                  not right.ctype.arg.is_complete()):
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
    comp_cmd = compare_cmds.LessCmp


class GreaterThan(_Relational):
    comp_cmd = compare_cmds.GreaterCmp


class LessThanOrEq(_Relational):
    comp_cmd = compare_cmds.LessOrEqCmp


class GreaterThanOrEq(_Relational):
    comp_cmd = compare_cmds.GreaterOrEqCmp


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


class _SizeofNode(_RExprNode):
    """Base class for common logic for the two sizeof nodes."""

    def __init__(self):
        super().__init__()

    def sizeof_ctype(self, ctype, range, il_code):
        """Raise CompilerError if ctype is not valid as sizeof argument."""

        if ctype.is_function():
            err = "sizeof argument cannot have function type"
            raise CompilerError(err, range)

        if ctype.is_incomplete():
            err = "sizeof argument cannot have incomplete type"
            raise CompilerError(err, range)

        out = ILValue(ctypes.unsig_longint)
        il_code.register_literal_var(out, ctype.size)
        return out


class SizeofExpr(_SizeofNode):
    """Node representing sizeof with expression operand.

    expr (_ExprNode) - the expression to get the size of
    """
    def __init__(self, expr):
        super().__init__()
        self.expr = expr

    def make_il(self, il_code, symbol_table, c):
        """Return a compile-time integer literal as the expression size."""

        dummy_il_code = il_code.copy()
        expr = self.expr.make_il_raw(dummy_il_code, symbol_table, c)
        return self.sizeof_ctype(expr.ctype, self.expr.r, il_code)


class SizeofType(_SizeofNode, Declaration):
    """Node representing sizeof with abstract type as operand.

    node (decl_nodes.Root) - a declaration tree for the type
    """
    def __init__(self, node):
        _SizeofNode.__init__(self)
        Declaration.__init__(self, node)   # sets self.node = node

    def make_il(self, il_code, symbol_table, c):
        """Return a compile-time integer literal as the expression size."""

        self.set_self_vars(il_code, symbol_table, c)
        base_type, _ = self.make_specs_ctype(self.node.specs, False)
        ctype, _ = self.make_ctype(self.node.decls[0], base_type)
        return self.sizeof_ctype(ctype, self.node.decls[0].r, il_code)


class Cast(Declaration, _RExprNode):
    """Node representing a cast operation, like `(void*)p`.

    node (decl_nodes.Root) - a declaration tree for this line

    TODO: Share code between Cast and Declaration nodes more cleanly.
    """
    def __init__(self, node, expr):
        Declaration.__init__(self, node)   # sets self.node = node
        _RExprNode.__init__(self)

        self.expr = expr

    def make_il(self, il_code, symbol_table, c):
        """Make IL for this cast operation."""

        self.set_self_vars(il_code, symbol_table, c)
        base_type, _ = self.make_specs_ctype(self.node.specs, False)
        ctype, _ = self.make_ctype(self.node.decls[0], base_type)

        if not ctype.is_void() and not ctype.is_scalar():
            err = "can only cast to scalar or void type"
            raise CompilerError(err, self.node.decls[0].r)

        il_value = self.expr.make_il(il_code, symbol_table, c)
        if not il_value.ctype.is_scalar():
            err = "can only cast from scalar type"
            raise CompilerError(err, self.r)

        return set_type(il_value, ctype, il_code)


class AddrOf(_RExprNode):
    """Address-of expression."""

    def __init__(self, expr):
        """Initialize node."""
        super().__init__()
        self.expr = expr

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""
        lvalue = self.expr.lvalue(il_code, symbol_table, c)
        if lvalue:
            return lvalue.addr(il_code)
        else:
            err = "operand of unary '&' must be lvalue"
            raise CompilerError(err, self.expr.r)


class Deref(_LExprNode):
    """Dereference expression."""

    def __init__(self, expr):
        """Initialize node."""
        super().__init__()
        self.expr = expr

    def _lvalue(self, il_code, symbol_table, c):
        addr = self.expr.make_il(il_code, symbol_table, c)

        if not addr.ctype.is_pointer():
            err = "operand of unary '*' must have pointer type"
            raise CompilerError(err, self.expr.r)

        return IndirectLValue(addr)


class ArraySubsc(_LExprNode):
    """Array subscript."""

    def __init__(self, head, arg):
        """Initialize node."""
        super().__init__()
        self.head = head
        self.arg = arg

    def _lvalue(self, il_code, symbol_table, c):
        """Return lvalue form of this node.

        We have two main cases here. The first case covers most simple
        situations, like `array[5]` or `array[x+3]`, and the second case
        covers more complex situations like `array[4][2]` or an array
        within a struct.

        In the first case, one of the two operands is a DirectLValue array
        (i.e. just a variable, not a lookup into another object). This
        means it will have a spot in memory assigned to it by the register
        allocator, and we can return a RelativeLValue object from this
        function. This case corresponds to `matched` being True. A
        RelativeLValue object usually becomes an assembly command like
        `[rbp-40+3*rax]`, which is more efficient than manually computing
        the address like happens in the second case.

        In the second case, neither operand is a DirectLValue array. This is
        the case for two-dimensional arrays, for example. Here, we proceed
        naively and get the address for the pointer side. This is a little
        bit less efficient. Ideally, in cases like `array[2][4]` where the
        lookup address could be computed at compile-time, we'd be able to do
        that, but this is not yet supported (TODO).

        """

        # One operand should be pointer to complete object type, and the
        # other should be any integer type.

        head_lv = self.head.lvalue(il_code, symbol_table, c)
        arg_lv = self.arg.lvalue(il_code, symbol_table, c)

        matched = False
        if isinstance(head_lv, DirectLValue) and head_lv.ctype().is_array():
            array, arith = self.head, self.arg
            matched = True
        elif isinstance(arg_lv, DirectLValue) and arg_lv.ctype().is_array():
            array, arith = self.arg, self.head
            matched = True

        if matched:
            # If one operand was a DirectLValue array
            array_val = array.make_il_raw(il_code, symbol_table, c)
            arith_val = arith.make_il(il_code, symbol_table, c)

            if arith_val.ctype.is_integral():
                return self.array_subsc(array_val, arith_val)

        else:
            # Neither operand was a DirectLValue array
            head_val = self.head.make_il(il_code, symbol_table, c)
            arg_val = self.arg.make_il(il_code, symbol_table, c)

            if head_val.ctype.is_pointer() and arg_val.ctype.is_integral():
                return self.pointer_subsc(head_val, arg_val, il_code)
            elif arg_val.ctype.is_pointer() and head_val.ctype.is_integral():
                return self.pointer_subsc(head_val, arg_val, il_code)

        descrip = "invalid operand types for array subscriping"
        raise CompilerError(descrip, self.r)

    def pointer_subsc(self, point, arith, il_code):
        """Return the LValue for this node.

        This function is called in the case where one operand is a pointer
        and the other operand is an integer.
        """
        if not point.ctype.arg.is_complete():
            err = "cannot subscript pointer to incomplete type"
            raise CompilerError(err, self.r)

        shift = get_size(point.ctype.arg, arith, il_code)
        out = ILValue(point.ctype)
        il_code.add(math_cmds.Add(out, point, shift))
        return IndirectLValue(out)

    def array_subsc(self, array, arith):
        """Return the LValue for this node.

        This function is called in the case where one operand is an array
        and the other operand is an integer.
        """
        el = array.ctype.el
        return RelativeLValue(el, array, el.size, arith)


class _ObjLookup(_LExprNode):
    """Struct/union object lookup (. or ->)"""

    def __init__(self, head, member):
        """Initialize node."""
        super().__init__()
        self.head = head
        self.member = member

    def get_offset_info(self, struct_ctype):
        """Given a struct ctype, return the member offset and ctype.

        If the given ctype is None, emits the error for requesting a member
        in something not a structure or union.
        """
        if not struct_ctype or not struct_ctype.is_struct_union():
            err = "request for member in something not a structure or union"
            raise CompilerError(err, self.r)

        offset, ctype = struct_ctype.get_offset(self.member.content)
        if offset is None:
            err = f"structure or union has no member '{self.member.content}'"
            raise CompilerError(err, self.r)

        if struct_ctype.is_const():
            ctype = ctype.make_const()

        return offset, ctype


class ObjMember(_ObjLookup):
    """Struct/union object member (. operator)"""

    def _lvalue(self, il_code, symbol_table, c):
        head_lv = self.head.lvalue(il_code, symbol_table, c)
        struct_ctype = head_lv.ctype() if head_lv else None
        offset, ctype = self.get_offset_info(struct_ctype)

        if isinstance(head_lv, DirectLValue):
            head_val = self.head.make_il(il_code, symbol_table, c)
            return RelativeLValue(ctype, head_val, offset)
        else:
            struct_addr = head_lv.addr(il_code)

            shift = ILValue(ctypes.longint)
            il_code.register_literal_var(shift, str(offset))

            out = ILValue(PointerCType(ctype))
            il_code.add(math_cmds.Add(out, struct_addr, shift))
            return IndirectLValue(out)


class ObjPtrMember(_ObjLookup):
    """Struct/union pointer object member (-> operator)"""

    def _lvalue(self, il_code, symbol_table, c):
        struct_addr = self.head.make_il(il_code, symbol_table, c)
        if not struct_addr.ctype.is_pointer():
            err = "first argument of '->' must have pointer type"
            raise CompilerError(err, self.r)

        offset, ctype = self.get_offset_info(struct_addr.ctype.arg)
        shift = ILValue(ctypes.longint)
        il_code.register_literal_var(shift, str(offset))

        out = ILValue(PointerCType(ctype))
        il_code.add(math_cmds.Add(out, struct_addr, shift))
        return IndirectLValue(out)


class FuncCall(_RExprNode):
    """Function call.

    func - Expression of type function pointer
    args - List of expressions for each argument
    """
    def __init__(self, func, args):
        """Initialize node."""
        super().__init__()
        self.func = func
        self.args = args

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""

        # This is of function pointer type, so func.arg is the function type.
        func = self.func.make_il(il_code, symbol_table, c)

        if not func.ctype.is_pointer() or not func.ctype.arg.is_function():
            descrip = "called object is not a function pointer"
            raise CompilerError(descrip, self.func.r)
        elif (func.ctype.arg.ret.is_incomplete()
              and not func.ctype.arg.ret.is_void()):
            # TODO: C11 spec says a function cannot return an array type,
            # but I can't determine how a function would ever be able to return
            # an array type.
            descrip = "function returns non-void incomplete type"
            raise CompilerError(descrip, self.func.r)

        if func.ctype.arg.no_info:
            final_args = self._get_args_without_prototype(
                il_code, symbol_table, c)
        else:
            final_args = self._get_args_with_prototype(
                func.ctype.arg, il_code, symbol_table, c)

        ret = ILValue(func.ctype.arg.ret)
        il_code.add(control_cmds.Call(func, final_args, ret))
        return ret

    def _get_args_without_prototype(self, il_code, symbol_table, c):
        """Return list of argument ILValues for function this represents.

        Use _get_args_without_prototype when the function this represents
        has no prototype. This function only performs integer promotion on the
        arguments before passing them to the called function.
        """
        final_args = []
        for arg_given in self.args:
            arg = arg_given.make_il(il_code, symbol_table, c)

            # perform integer promotions
            if arg.ctype.is_arith() and arg.ctype.size < 4:
                arg = set_type(arg, ctypes.integer, il_code)

            final_args.append(arg)
        return final_args

    def _get_args_with_prototype(self, func_ctype, il_code, symbol_table, c):
        """Return list of argument ILValues for function this represents.

        Use _get_args_with_prototype when the function this represents
        has a prototype. This function converts all passed arguments to
        expected types.
        """
        arg_types = func_ctype.args

        if len(arg_types) != len(self.args):
            err = ("incorrect number of arguments for function call"
                   f" (expected {len(arg_types)}, have {len(self.args)})")

            if self.args:
                raise CompilerError(err, self.args[-1].r)
            else:
                raise CompilerError(err, self.r)

        final_args = []
        for arg_given, arg_type in zip(self.args, arg_types):
            arg = arg_given.make_il(il_code, symbol_table, c)
            check_cast(arg, arg_type, arg_given.r)
            final_args.append(
                set_type(arg, arg_type.make_unqual(), il_code))
        return final_args
