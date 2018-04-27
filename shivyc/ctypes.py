"""This module defines all of the C types recognized by the compiler."""

import copy

import shivyc.token_kinds as token_kinds


class CType:
    """Represents a C type, like `int` or `double` or a struct or union.

    size (int) - The result of sizeof on this type.
    """

    def __init__(self, size, const=False):
        """Initialize type."""
        self.size = size
        self.const = const

        # Required because casting to bool is special in C11.
        self._bool = False

        # Required for super hacky struct trick, see the weak_compat
        # function for the struct.
        self._orig = self

    def weak_compat(self, other):
        """Check for weak compatibility with `other` ctype.

        Two types are "weakly compatible" if their unqualified version are
        compatible.
        """
        raise NotImplementedError

    def is_complete(self):
        """Check whether this is a complete type."""
        return False

    def is_incomplete(self):
        """Check whether this is an incomplete type.

        An object type must be either complete or incomplete.
        """
        return False

    def is_object(self):
        """Check whether this is an object type."""
        return False

    def is_arith(self):
        """Check whether this is an arithmetic type."""
        return False

    def is_integral(self):
        """Check whether this is an integral type."""
        return False

    def is_pointer(self):
        """Check whether this is a pointer type."""
        return False

    def is_function(self):
        """Check whether this is a function type."""
        return False

    def is_void(self):
        """Check whether this is a void type."""
        return False

    def is_bool(self):
        """Check whether this is a boolean type."""
        return self._bool

    def is_array(self):
        """Check whether this is an array type."""
        return False

    def is_struct_union(self):
        """Check whether this has struct or union type."""
        return False

    def make_unsigned(self):
        """Return an unsigned version of this type."""
        raise NotImplementedError

    def compatible(self, other):
        """Check whether given `other` C type is compatible with self."""
        return self.weak_compat(other) and self.const == other.const

    def is_scalar(self):
        """Check whether this has scalar type."""
        return self.is_arith() or self.is_pointer()

    def is_const(self):
        """Check whether this is a const type."""
        return self.const

    def make_const(self):
        """Return a const version of this type."""
        const_self = copy.copy(self)
        const_self.const = True
        return const_self

    def make_unqual(self):
        """Return an unqualified version of this type."""
        unqual_self = copy.copy(self)
        unqual_self.const = False
        return unqual_self


class IntegerCType(CType):
    """Represents an integer C type, like 'unsigned long' or 'bool'.

    This class must be instantiated only once for each distinct integer C type.

    size (int) - The result of sizeof on this type.
    signed (bool) - Whether this type is signed.

    """

    def __init__(self, size, signed):
        """Initialize type."""
        self.signed = signed
        super().__init__(size)

    def weak_compat(self, other):
        """Check whether two types are compatible."""

        # TODO: _orig stuff is hacky...
        # Find a more reliable way to talk about types being equal.
        return (other._orig == self._orig and self.signed == other.signed and
                self.is_bool() == other.is_bool())

    def is_complete(self):
        """Check if this is a complete type."""
        return True

    def is_object(self):
        """Check if this is an object type."""
        return True

    def is_arith(self):
        """Check whether this is an arithmetic type."""
        return True

    def is_integral(self):
        """Check whether this is an integral type."""
        return True

    def make_unsigned(self):
        """Return an unsigned version of this type."""
        unsig_self = copy.copy(self)
        unsig_self.signed = False
        return unsig_self


class VoidCType(CType):
    """Represents a void C type.

    This class must be instantiated only once.

    """

    def __init__(self):
        """Initialize type."""
        super().__init__(1)

    def weak_compat(self, other):
        """Return True iff other is a compatible type to self."""
        return other.is_void()

    def is_incomplete(self):
        """Check if this is a complete type."""
        return True

    def is_void(self):
        """Check whether this is a void type."""
        return True

    def is_object(self):
        return True


class PointerCType(CType):
    """Represents a pointer C type.

    arg (CType) - Type pointed to.

    """

    def __init__(self, arg, const=False):
        """Initialize type."""
        self.arg = arg
        super().__init__(8, const)

    def weak_compat(self, other):
        """Return True iff other is a compatible type to self."""
        return other.is_pointer() and self.arg.compatible(other.arg)

    def is_complete(self):
        """Check if this is a complete type."""
        return True

    def is_pointer(self):
        """Check whether this is a pointer type."""
        return True

    def is_object(self):
        """Check if this is an object type."""
        return True


class ArrayCType(CType):
    """Represents an array C type.

    el (CType) - Type of each element in array.
    n (int) - Size of array (or None if this is incomplete)

    """

    def __init__(self, el, n):
        """Initialize type."""
        self.el = el
        self.n = n
        super().__init__((n or 1) * self.el.size)

    def compatible(self, other):
        """Return True iff other is a compatible type to self."""
        return (other.is_array() and self.el.compatible(other.el) and
                (self.n is None or other.n is None or self.n == other.n))

    def is_complete(self):
        """Check if this is a complete type."""
        return self.n is not None

    def is_incomplete(self):
        return not self.is_complete()

    def is_object(self):
        """Check if this is an object type."""
        return True

    def is_array(self):
        """Check whether this is an array type."""
        return True


class FunctionCType(CType):
    """Represents a function C type.

    args (List(CType)) - List of the argument ctypes, from left to right, or
    None if unspecified.
    ret (CType) - Return value of the function.
    no_info (bool) - True if the function does not have any parameter info.
    This occurs when the function is declared as `int f();` with nothing in
    between the parentheses.
    """

    def __init__(self, args, ret, no_info):
        """Initialize type."""
        self.args = args
        self.ret = ret
        self.no_info = no_info
        super().__init__(1)

    def weak_compat(self, other):
        """Return True iff other is a compatible type to self."""

        if not other.is_function():
            return False
        elif not self.ret.compatible(other.ret):
            return False
        elif not self.no_info and not other.no_info:
            if len(self.args) != len(other.args):
                return False
            elif any(not a1.compatible(a2) for a1, a2 in
                     zip(self.args, other.args)):
                return False

        # TODO: There are special rules for compatibility between a function
        # with parameter list and a function without parameter list. See
        # 6.7.6.3.15.

        return True

    def is_function(self):
        """Check if this is a function type."""
        return True


class _UnionStructCType(CType):
    """Base class for struct and union C types.

    tag - Name of the struct/union as a string, or None if it's anonymous

    members - List of members of this type. Each element of the list should be
    a tuple (str, ctype) where `str` is the string of the identifier used to
    access that member and ctype is the ctype of that member.
    complete - Boolean indicating whether this type is complete
    """

    def __init__(self, tag, members=None):
        self.tag = tag
        self.members = members
        self.offsets = {}
        super().__init__(1)

    def weak_compat(self, other):
        """Return True if other is a compatible type to self.

        Within a single translation unit, two structs are compatible if
        they are the exact same declaration.
        """
        return self._orig is other._orig

    def is_complete(self):
        """Check whether this is a complete type."""
        return self.members is not None

    def is_incomplete(self):
        return not self.is_complete()

    def is_object(self):
        """Check whether this is an object type."""
        return True

    def is_struct_union(self):
        """Check whether this has struct or union type."""
        return True

    def get_offset(self, member):
        """Get the offset and type of a given member.

        If the member does not exist, this function returns None tuple.
        """
        return self.offsets.get(member, (None, None))

    def set_members(self, members):
        """Add the given members to this type.

        The members list is given in the format as described in the class
        description.
        """
        raise NotImplementedError


class StructCType(_UnionStructCType):
    """Represents a struct ctype."""

    def set_members(self, members):
        self.members = members

        cur_offset = 0
        for member, ctype in members:
            self.offsets[member] = cur_offset, ctype
            cur_offset += ctype.size

        self.size = cur_offset


class UnionCType(_UnionStructCType):
    """Represents a union ctype.

    Similar to struct type, but different offset is used.
    """

    def set_members(self, members):
        self.members = members
        self.size = max([ctype.size for _, ctype in members], default=0)
        for member, ctype in members:
            self.offsets[member] = 0, ctype


# These definitions are here to permit convenient creation of new integer,
# char, etc. types. However, DO NOT test whether a ctype is one of these by
# checking equality. That is, do not use `ctype == ctypes.integer` to check
# whether `ctype` is an integer. This is because functions like
# "make_unsigned" or "make_const" return a copy of the type, so equality
# checking will not work.


void = VoidCType()

bool_t = IntegerCType(1, False)
bool_t._bool = True

char = IntegerCType(1, True)
unsig_char = IntegerCType(1, False)
unsig_char_max = 255

short = IntegerCType(2, True)
unsig_short = IntegerCType(2, False)

integer = IntegerCType(4, True)
unsig_int = IntegerCType(4, False)
int_max = 2147483647
int_min = -2147483648

longint = IntegerCType(8, True)
unsig_longint = IntegerCType(8, False)
long_max = 9223372036854775807
long_min = -9223372036854775808


simple_types = {token_kinds.void_kw: void,
                token_kinds.bool_kw: bool_t,
                token_kinds.char_kw: char,
                token_kinds.short_kw: short,
                token_kinds.int_kw: integer,
                token_kinds.long_kw: longint}
