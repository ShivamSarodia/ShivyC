"""Memory operation and member access expression nodes in the AST."""

import shivyc.ctypes as ctypes
import shivyc.il_cmds.math as math_cmds
from shivyc.ctypes import PointerCType
from shivyc.errors import CompilerError
from shivyc.il_gen import ILValue
from shivyc.tree.expr_base import _RExprNode, _LExprNode
from shivyc.tree.utils import (IndirectLValue, DirectLValue, RelativeLValue,
                               get_size)


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
