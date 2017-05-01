"""Nodes in the AST which represent expression values."""

import shivyc.ctypes as ctypes
import shivyc.tree.nodes as nodes
import shivyc.il_cmds.compare as compare_cmds
import shivyc.il_cmds.control as control_cmds
import shivyc.il_cmds.math as math_cmds
import shivyc.il_cmds.value as value_cmds

from shivyc.ctypes import ArrayCType, PointerCType
from shivyc.errors import CompilerError, error_collector
from shivyc.il_gen import ILValue
from shivyc.tree.utils import (LValue, check_cast, set_type, arith_convert,
                               get_size)


class _RExprNode(nodes.Node):
    """Base class for representing an rvalue expression node in the AST.

    There are two types of expression nodes, RExprNode and LExprNode.
    An expression node which can be used as an lvalue (that is, an expression
    node which can be the argument of an address-of operator) derives from
    LExprNode. Expression nodes which cannot be used as lvalues derive from
    RExprNode.

    An RExprNode-derived node implements only the make_il function.
    """

    def __init__(self):
        super().__init__()

    def lvalue(self, il_code, symbol_table, c):
        """Return None, because this node does not represent an LValue."""
        return None

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


class _LExprNode(nodes.Node):
    """Base class for representing an lvalue expression node in the AST.

    See RExprNode for general explanation.

    An LExprNode-derived node implements only the _lvalue function. This
    function returns an LValue object representing this node. The
    implementation of this class automatically sets up the appropriate
    make_il function which calls the lvalue implementation.
    """

    def __init__(self):
        super().__init__()
        self._cache_lvalue = None

    def _lvalue(self, il_code, symbol_table, c):
        """Return an LValue object representing this node.

        Do not call this function directly, because it does not cache the
        result. Multiple calls to this function may generate multiple error
        messages or output repeated code to il_code.
        """
        raise NotImplementedError

    def lvalue(self, il_code, symbol_table, c):
        """Return an LValue object representing this node."""
        if not self._cache_lvalue:
            self._cache_lvalue = self._lvalue(il_code, symbol_table, c)
        return self._cache_lvalue

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node and return decayed version of result."""

        lvalue = self.lvalue(il_code, symbol_table, c)

        # Decay array
        if lvalue and lvalue.ctype().is_array():
            addr = lvalue.addr(il_code)
            return set_type(addr, PointerCType(lvalue.ctype().el), il_code)

        # Decay function
        elif lvalue and lvalue.ctype().is_function():
            return lvalue.addr(il_code)

        # Nothing to decay
        else:
            return lvalue.val(il_code)


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

        # Literal integer 0 is a null pointer constant
        if v == 0:
            il_value.null_ptr_const = True

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
        return LValue(LValue.DIRECT, il_value)


class Identifier(_LExprNode):
    """Expression that is a single identifier."""

    def __init__(self, identifier):
        """Initialize node."""
        super().__init__()
        self.identifier = identifier

    def _lvalue(self, il_code, symbol_table, c):
        var = symbol_table.lookup_tok(self.identifier)
        return LValue(LValue.DIRECT, var)


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

        if left.ctype.is_arith() and right.ctype.is_arith():
            left, right = arith_convert(left, right, il_code)
            return self._arith(left, right, il_code)
        else:
            return self._nonarith(left, right, il_code)

    default_il_cmd = None

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

    def _nonarith(self, left, right, il_code):
        """Make addition code if either operand is non-arithmetic type."""

        # One operand should be pointer to complete object type, and the
        # other should be any integer type.
        # TODO: "complete object type", not just pointer.
        if left.ctype.is_pointer() and right.ctype.is_integral():
            arith, pointer = right, left
        elif right.ctype.is_pointer() and left.ctype.is_integral():
            arith, pointer = left, right
        else:
            err = "invalid operand types for addition"
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

    def _nonarith(self, left, right, il_code):
        """Make subtraction code if both operands are non-arithmetic type."""

        # Both operands are pointers to compatible object types
        # TODO: this isn't quite right when we allow qualifiers
        if (left.ctype.is_pointer() and right.ctype.is_pointer()
             and left.ctype.compatible(right.ctype)):

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

    def _nonarith(self, left, right, il_code):
        err = "invalid operand types for multiplication"
        raise CompilerError(err, self.op.r)


class Div(_ArithBinOp):
    """Expression that is quotient of two expressions."""

    def __init__(self, left, right, op):
        """Initialize node."""
        super().__init__(left, right, op)

    default_il_cmd = math_cmds.Div

    def _nonarith(self, left, right, il_code):
        err = "invalid operand types for division"
        raise CompilerError(err, self.op.r)


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
        if left.ctype.is_pointer() and right.null_ptr_const:
            right = set_type(right, left.ctype, il_code)
        elif right.ctype.is_pointer() and left.null_ptr_const:
            left = set_type(left, right.ctype, il_code)

        # If both operands are not pointer types, warn!
        if not left.ctype.is_pointer() or not right.ctype.is_pointer():
            err = "comparison between incomparable types"
            error_collector.add(CompilerError(err, self.op.r, True))

        # If one side is pointer to void, cast the other to same.
        elif left.ctype.arg.is_void():
            check_cast(right, left.ctype, self.op.r)
            right = set_type(right, left.ctype, il_code)
        elif right.ctype.arg.is_void():
            check_cast(left, right.ctype, self.op.r)
            left = set_type(left, right.ctype, il_code)

        # If both types are still incompatible, warn!
        elif not left.ctype.compatible(right.ctype):
            descrip = "comparison between distinct pointer types"
            error_collector.add(CompilerError(descrip, self.op.r, True))

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

        left = self.left.make_il(il_code, symbol_table, c)
        il_code.add(value_cmds.Set(out, init))
        il_code.add(self.jump_cmd(left, set_out))
        right = self.right.make_il(il_code, symbol_table, c)
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
            err = "operand of {} operator not a modifiable lvalue"
            raise CompilerError(err.format(self.descrip), self.expr.r)

        val = self.expr.make_il(il_code, symbol_table, c)
        one = ILValue(val.ctype)
        if val.ctype.is_arith():
            il_code.register_literal_var(one, 1)
        elif val.ctype.is_pointer():
            il_code.register_literal_var(one, val.ctype.arg.size)
        else:
            err = "invalid type for {} operator"
            raise CompilerError(err.format(self.descrip), self.expr.r)

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


class BoolNot(_RExprNode):
    """Boolean not."""

    def __init__(self, expr):
        """Initialize node."""
        super().__init__()
        self.expr = expr

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""

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

        expr = self.expr.make_il(il_code, symbol_table, c)
        il_code.add(value_cmds.Set(out, one))
        il_code.add(control_cmds.JumpZero(expr, end))
        il_code.add(value_cmds.Set(out, zero))
        il_code.add(control_cmds.Label(end))

        return out


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

        return LValue(LValue.INDIRECT, addr)


class ArraySubsc(_LExprNode):
    """Array subscript."""

    def __init__(self, head, arg, op):
        """Initialize node."""
        super().__init__()
        self.head = head
        self.arg = arg
        self.op = op

    def _lvalue(self, il_code, symbol_table, c):
        """Return lvalue form of this node."""

        # One operand should be pointer to complete object type, and the
        # other should be any integer type.

        head_val = self.head.make_il(il_code, symbol_table, c)
        arg_val = self.arg.make_il(il_code, symbol_table, c)

        # Otherwise, compute the lvalue
        if head_val.ctype.is_pointer() and arg_val.ctype.is_integral():
            arith, point = arg_val, head_val
        elif head_val.ctype.is_integral() and arg_val.ctype.is_pointer():
            arith, point = head_val, arg_val
        else:
            descrip = "invalid operand types for array subscriping"
            raise CompilerError(descrip, self.r)

        shift = get_size(point.ctype.arg, arith, il_code)
        out = ILValue(point.ctype)
        il_code.add(math_cmds.Add(out, point, shift))
        return LValue(LValue.INDIRECT, out)


class FuncCall(_RExprNode):
    """Function call.

    func - Expression of type function pointer
    args - List of expressions for each argument
    tok - Opening parenthesis of this function call, for error reporting

    """

    def __init__(self, func, args, tok):
        """Initialize node."""
        super().__init__()
        self.func = func
        self.args = args
        self.tok = tok

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""

        # This is of function pointer type, so func.arg is the function type.
        func = self.func.make_il(il_code, symbol_table, c)

        if not func.ctype.is_pointer() or not func.ctype.arg.is_function():
            descrip = "called object is not a function pointer"
            raise CompilerError(descrip, self.func.r)

        if not func.ctype.arg.args:
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
        # if only parameter is of type void, expect no arguments
        if (len(func_ctype.args) == 1 and
             func_ctype.args[0].is_void()):
            arg_types = []
        else:
            arg_types = func_ctype.args
        if len(arg_types) != len(self.args):
            err = ("incorrect number of arguments for function call" +
                   " (expected {}, have {})").format(len(arg_types),
                                                     len(self.args))

            if self.args:
                raise CompilerError(err, self.args[-1].r)
            else:
                raise CompilerError(err, self.tok.r)

        final_args = []
        for arg_given, arg_type in zip(self.args, arg_types):
            arg = arg_given.make_il(il_code, symbol_table, c)
            check_cast(arg, arg_type, arg_given.r)
            final_args.append(set_type(arg, arg_type, il_code))
        return final_args
