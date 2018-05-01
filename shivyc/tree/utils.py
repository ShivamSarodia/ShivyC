"""Utility objects for the AST nodes and IL generation steps of ShivyC."""

from contextlib import contextmanager

import shivyc.ctypes as ctypes
import shivyc.il_cmds.value as value_cmds
import shivyc.il_cmds.math as math_cmds

from shivyc.ctypes import PointerCType
from shivyc.errors import CompilerError, error_collector
from shivyc.il_gen import ILValue


class LValue:
    """Represents an LValue."""

    def ctype(self):
        """Return the ctype that is stored by this LValue.

        For example, if this LValue represents a dereferenced pointer to an
        integer, then this function returns a ctype of integer.
        """
        raise NotImplementedError

    def set_to(self, rvalue, il_code, r):
        """Emit code to set the given lvalue to the given ILValue.

        rvalue (ILValue) - rvalue to set this lvalue to
        il_code (ILCode) - ILCode object to add generated code
        r (Range) - Range for warning/error messages
        return - ILValue representing the result of this operation

        """
        raise NotImplementedError

    def addr(self, il_code):
        """Generate code for and return address of this lvalue."""
        raise NotImplementedError

    def val(self, il_code):
        """Generate code for and return the value currently stored."""
        raise NotImplementedError

    def modable(self):
        """Return whether this is a modifiable lvalue."""

        # TODO: add "is not const qualified" and "if struct/union, has no
        # const qualified member"
        ctype = self.ctype()
        if ctype.is_array():
            return False
        if ctype.is_incomplete():
            return False
        if ctype.is_const():
            return False
        if (ctype.is_struct_union() and
             any(m[1].is_const() for m in ctype.members)):
            return False

        return True


class DirectLValue(LValue):
    """Represents a direct LValue.

    A direct LValue stores an ILValue to which this LValue refers. For
    example, a variable is a direct LValue.
    """
    def __init__(self, il_value):
        """Initialize DirectLValue with the IL value it represents."""
        self.il_value = il_value

    def ctype(self):  # noqa D102
        return self.il_value.ctype

    def set_to(self, rvalue, il_code, r):  # noqa D102
        check_cast(rvalue, self.ctype(), r)
        return set_type(rvalue, self.ctype(), il_code, self.il_value)

    def addr(self, il_code):  # noqa D102
        out = ILValue(PointerCType(self.il_value.ctype))
        il_code.add(value_cmds.AddrOf(out, self.il_value))
        return out

    def val(self, il_code):  # noqa D102
        return self.il_value


class IndirectLValue(LValue):
    """Represents an indirect LValue.

    An indirect LValue stores an ILValue which is the address of the object
    represented by this LValue. For example, a dereferenced pointer or an
    array subscripted value is an IndirectLValue.
    """
    def __init__(self, addr_val):
        """Initialize the IndirectLValue.

        addr_val must be an ILValue containing the address of the object
        pointed to by this LValue.
        """
        self.addr_val = addr_val

    def ctype(self):  # noqa D102
        return self.addr_val.ctype.arg

    def set_to(self, rvalue, il_code, r):  # noqa D102
        check_cast(rvalue, self.ctype(), r)
        right_cast = set_type(rvalue, self.ctype(), il_code)
        il_code.add(value_cmds.SetAt(self.addr_val, right_cast))
        return right_cast

    def addr(self, il_code):  # noqa D102
        return self.addr_val

    def val(self, il_code):  # noqa D102
        out = ILValue(self.ctype())
        il_code.add(value_cmds.ReadAt(out, self.addr_val))
        return out


class RelativeLValue(LValue):
    """Represents a relative LValue.

    A relative LValue is used to represent an LValue that is located in
    memory relative to the position of another ILValue. For example,
    in the expression `array[5] = 3`, the `array[5]` is a RelativeLValue
    because it represents a value offset by 5 from the ILValue of array.

    ctype - The ctype that can be stored in this RelativeLValue. In the
    example above, this would be the integer ctype.

    base - ILValue representing the base object. Note this is the base
    object itself, not the address of the base object.

    chunk - A Python integer representing the size of each chunk of offset.

    count - If provided, an integral ILValue representing the number of
    chunks of offset.

    In summary, if `count` is provided, then the address of the object
    represented by this LValue is:

        &base + chunk * count

    and if `count` is not provided, the address is just

        &base + chunk

    """
    def __init__(self, ctype, base, chunk=0, count=None):
        self._ctype = ctype
        self.base = base
        self.chunk = chunk
        self.count = count

        self.fixed_count = None
        self.fixed_chunk = None

    def _fix_chunk_count(self, il_code):
        """Convert chunk and count so that chunk is in {1, 2, 4, 8}.

        The Rel commands requre that chunk be in {1, 2, 4, 8}. If the
        given chunk value is not in this set, we multiply count and divide
        chunk by an appropriate value so that chunk is in {1, 2, 4, 8},
        and then return the new value of chunk and the new value of count.

        In addition, this command moves `count` to a 64-bit value.
        """
        # Cache the value of fixed_chunk and fixed_count so it is not
        # recomputed unnecessarily
        if self.fixed_chunk or self.fixed_count:
            return

        if not self.count:
            self.fixed_chunk, self.fixed_count = self.chunk, self.count
            return

        # TODO: Technically, if count is an unsigned long and `chunk` is in
        # `sizes`, we don't need to emit a SET command.
        resized_count = set_type(self.count, ctypes.longint, il_code)

        sizes = [8, 4, 2, 1]
        if self.chunk in sizes:
            self.fixed_chunk, self.fixed_count = self.chunk, resized_count
            return

        # Select the biggest legal size that divides given chunk size
        for new_chunk in sizes:
            if self.chunk % new_chunk == 0:
                break

        self.fixed_chunk = new_chunk

        scale = ILValue(ctypes.longint)
        scale_factor = str(int(self.chunk / new_chunk))
        il_code.register_literal_var(scale, scale_factor)

        self.fixed_count = ILValue(ctypes.longint)
        il_code.add(math_cmds.Mult(self.fixed_count, resized_count, scale))

    def ctype(self):
        return self._ctype

    def set_to(self, rvalue, il_code, r):
        self._fix_chunk_count(il_code)
        check_cast(rvalue, self.ctype(), r)
        right_cast = set_type(rvalue, self.ctype(), il_code)
        il_code.add(value_cmds.SetRel(
            right_cast, self.base, self.fixed_chunk, self.fixed_count))
        return right_cast

    def addr(self, il_code):
        self._fix_chunk_count(il_code)
        out = ILValue(PointerCType(self.ctype()))
        il_code.add(value_cmds.AddrRel(
            out, self.base, self.fixed_chunk, self.fixed_count))
        return out

    def val(self, il_code):
        self._fix_chunk_count(il_code)
        out = ILValue(self.ctype())
        il_code.add(value_cmds.ReadRel(
            out, self.base, self.fixed_chunk, self.fixed_count))
        return out


@contextmanager
def report_err():
    """Catch and add any errors to error collector."""
    try:
        yield
    except CompilerError as e:
        error_collector.add(e)


def check_cast(il_value, ctype, range):
    """Emit warnings/errors of casting il_value to given ctype.

    This method does not actually cast the values. If values cannot be
    cast, an error is raised by this method.

    il_value - ILValue to convert
    ctype - CType to convert to
    range - Range for error reporting

    """
    # Cast between compatible types is always okay
    if il_value.ctype.weak_compat(ctype):
        return

    # Cast between arithmetic types is always okay
    if ctype.is_arith() and il_value.ctype.is_arith():
        return

    # Cast between weak compatible structs is okay
    if (ctype.is_struct_union() and il_value.ctype.is_struct_union() and
         il_value.ctype.weak_compat(ctype)):
        return

    elif ctype.is_pointer() and il_value.ctype.is_pointer():

        # both operands are pointers to qualified or unqualified versions
        # of compatible types, and the type pointed to by the left has all
        # the qualifiers of the type pointed to by the right
        if (ctype.arg.weak_compat(il_value.ctype.arg) and
             (not il_value.ctype.arg.const or ctype.arg.const)):
            return

        # Cast between void pointer and pointer to object type okay
        elif (ctype.arg.is_void() and il_value.ctype.arg.is_object() and
              (not il_value.ctype.arg.const or ctype.arg.const)):
            return

        elif (ctype.arg.is_object() and il_value.ctype.arg.is_void() and
              (not il_value.ctype.arg.const or ctype.arg.const)):
            return

        # error on any other kind of pointer cast - TODO: better errors
        else:
            with report_err():
                err = "conversion from incompatible pointer type"
                raise CompilerError(err, range)
            return

    # Cast from null pointer constant to pointer okay
    elif ctype.is_pointer() and getattr(il_value.literal, "val", None) == 0:
        return

    # Cast from pointer to boolean okay
    elif ctype.is_bool() and il_value.ctype.is_pointer():
        return

    else:
        err = "invalid conversion between types"
        raise CompilerError(err, range)


def set_type(il_value, ctype, il_code, output=None):
    """If necessary, emit code to cast given il_value to the given ctype.

    If `output` is given, then this function expects output.ctype to be the
    same as ctype, sets `output` to the casted value, and returns output.

    If `output` is not given, this function returns an IL value with type
    ctype. If `il_value.ctype` matches given ctype, this function may return
    `il_value` directly. So, the return value should never have its value
    changed because this may affect the value in the given `il_value`.

    This function does no type checking and will never produce a warning or
    error.
    """
    if not output and il_value.ctype.compatible(ctype):
        return il_value
    elif output == il_value:
        return il_value
    elif not output and il_value.literal:
        output = ILValue(ctype)
        if ctype.is_integral():
            val = shift_into_range(il_value.literal.val, ctype)
        else:
            val = il_value.literal.val
        il_code.register_literal_var(output, val)
        return output
    else:
        if not output:
            output = ILValue(ctype)
        il_code.add(value_cmds.Set(output, il_value))
        return output


def arith_conversion_type(type1, type2):
    """Perform arithmetic type conversion.

    Accepts two arithmetic ctypes and returns the type these should be
    promoted to for computation.

    This functions disregards the qualifiers of the input, so it may or may
    not return a type with the same qualifier(s) as the input types.
    """
    # If an int can represent all values of the original type, the value is
    # converted to an int; otherwise, it is converted to an unsigned
    # int. These are called the integer promotions.

    # All types of size < 4 can fit in int, so we promote directly to int
    type1_promo = ctypes.integer if type1.size < 4 else type1
    type2_promo = ctypes.integer if type2.size < 4 else type2

    # If both operands have compatible types, then no further conversion is
    # needed.
    if type1_promo.weak_compat(type2_promo):
        return type1_promo

    # Otherwise, if both operands have signed integer types or both have
    # unsigned integer types, the operand with the type of lesser integer
    # conversion rank is converted to the type of the operand with greater
    # rank.
    elif type1_promo.signed == type2_promo.signed:
        return max([type1_promo, type2_promo], key=lambda t: t.size)

    # Otherwise, if the operand that has unsigned integer type has rank
    # greater or equal to the rank of the type of the other operand, then
    # the operand with signed integer type is converted to the type of the
    # operand with unsigned integer type.
    elif not type1_promo.signed and type1_promo.size >= type2_promo.size:
        return type1_promo
    elif not type2_promo.signed and type2_promo.size >= type1_promo.size:
        return type2_promo

    # Otherwise, if the type of the operand with signed integer type can
    # represent all of the values of the type of the operand with unsigned
    # integer type, then the operand with unsigned integer type is
    # converted to the type of the operand with signed integer type.
    elif type1_promo.signed and type1_promo.size > type2_promo.size:
        return type1_promo
    elif type2_promo.signed and type2_promo.size > type1_promo.size:
        return type2_promo

    # Otherwise, both operands are converted to the unsigned integer type
    # corresponding to the type of the operand with signed integer type.
    #
    # Commented because this code /should/ never be reached, because all
    # combinations will be caught by one of the above two conditions.
    #
    # elif type1_promo.signed:
    #     return type1_promo.make_unsigned()
    # elif type2_promo.signed:
    #     return type2_promo.make_unsigned()


def arith_convert(left, right, il_code):
    """Cast two arithmetic ILValues to a common converted type."""
    ctype = arith_conversion_type(left.ctype, right.ctype)
    return set_type(left, ctype, il_code), set_type(right, ctype, il_code)


def get_size(ctype, num, il_code):
    """Return ILValue representing total size of `num` objects of given ctype.

    ctype - CType of object to count
    num - Integral ILValue representing number of these objects
    """

    long_num = set_type(num, ctypes.longint, il_code)
    total = ILValue(ctypes.longint)
    size = ILValue(ctypes.longint)
    il_code.register_literal_var(size, str(ctype.size))
    il_code.add(math_cmds.Mult(total, long_num, size))

    return total


def shift_into_range(val, ctype):
    """Shift a numerical value into range for given integral ctype."""

    if ctype.signed:
        max_val = 1 << (ctype.size * 8 - 1)
        range = 2 * max_val
    else:
        max_val = 1 << ctype.size * 8
        range = max_val

    val = val % range
    if val >= max_val:
        val -= range

    return val
