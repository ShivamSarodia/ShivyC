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

        return (self.ctype().is_arith() or
                self.ctype().is_pointer() or
                self.ctype().is_void())


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
    def __init__(self, addr_val, offset=None, size=0):
        """Initialize the IndirectLValue.

        addr_val must be an ILValue.
        offset may be either an integral ILValue or a Python integer.
        size must be a Python integer among {1, 2, 4, 8, 16}

        Then, the object pointed to by this LValue is at:

        addr_val + offset * size

        TODO: offset/size are currently unimplemented!
        """
        self.addr_val = addr_val
        self.offset = offset
        self.size = size

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
    # Cast between same types is always okay
    if il_value.ctype == ctype:
        return

    # Cast between arithmetic types is always okay
    if ctype.is_arith() and il_value.ctype.is_arith():
        return

    elif ctype.is_pointer() and il_value.ctype.is_pointer():

        # Cast between compatible pointer types okay
        if ctype.compatible(il_value.ctype):
            return

        # Cast between void pointer and pointer to object type okay
        elif ctype.arg.is_void() and il_value.ctype.arg.is_object():
            return
        elif ctype.arg.is_object() and il_value.ctype.arg.is_void():
            return

        # Warn on any other kind of pointer cast
        else:
            with report_err():
                err = "conversion from incompatible pointer type"
                raise CompilerError(err, range, True)
            return

    # Cast from null pointer constant to pointer okay
    elif ctype.is_pointer() and il_value.null_ptr_const:
        return

    # Cast from pointer to boolean okay
    elif ctype == ctypes.bool_t and il_value.ctype.is_pointer():
        return

    else:
        err = "invalid conversion between types"
        raise CompilerError(err, range)


def set_type(il_value, ctype, il_code, output=None):
    """If necessary, emit code to cast given il_value to the given ctype.

    This function does no type checking and will never produce a warning or
    error.

    """
    # (no output value, and same types) OR (output is same as input)
    if (not output and il_value.ctype == ctype) or output == il_value:
        return il_value
    else:
        if not output:
            output = ILValue(ctype)
        il_code.add(value_cmds.Set(output, il_value))
        return output


def arith_conversion_type(type1, type2):
    """Perform arithmetic type conversion.

    Accepts two arithmetic ctypes and returns the type these should be
    promoted to for computation.
    """
    # If an int can represent all values of the original type, the value is
    # converted to an int; otherwise, it is converted to an unsigned
    # int. These are called the integer promotions.

    # All types of size < 4 can fit in int, so we promote directly to int
    type1_promo = ctypes.integer if type1.size < 4 else type1
    type2_promo = ctypes.integer if type2.size < 4 else type2

    # If both operands have the same type, then no further conversion is
    # needed.
    if type1_promo == type2_promo:
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
    elif type1_promo.signed:
        return ctypes.to_unsigned(type1_promo)
    elif type2_promo.signed:
        return ctypes.to_unsigned(type2_promo)


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
