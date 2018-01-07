"""This module defines all of the C types recognized by the compiler."""

import shivyc.token_kinds as token_kinds


class CType:
    """Represents a C type, like `int` or `double` or a struct.

    size (int) - The result of sizeof on this type.
    """

    def __init__(self, size):
        """Initialize type."""
        self.size = size

    def compatible(self, other):
        """Check whether given `other` C type is compatible with self."""
        raise NotImplementedError

    def is_complete(self):
        """Check whether this is a complete type."""
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

    def is_array(self):
        """Check whether this is an array type."""
        return False


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

    def compatible(self, other):
        """Check whether two types are compatible."""
        return other == self

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


class VoidCType(CType):
    """Represents a void C type.

    This class must be instantiated only once.

    """

    def __init__(self):
        """Initialize type."""
        super().__init__(1)

    def compatible(self, other):
        """Return True iff other is a compatible type to self."""
        return other == self

    def is_complete(self):
        """Check if this is a complete type."""
        return False

    def is_void(self):
        """Check whether this is a void type."""
        return True


class PointerCType(CType):
    """Represents a pointer C type.

    arg (CType) - Type pointed to.

    """

    def __init__(self, arg):
        """Initialize type."""
        self.arg = arg
        super().__init__(8)

    def compatible(self, other):
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
        super().__init__(n * self.el.size)

    def compatible(self, other):
        """Return True iff other is a compatible type to self."""
        return (other.is_array() and self.el.compatible(other.el) and
                (self.n is None or other.n is None or self.n == other.n))

    def is_complete(self):
        """Check if this is a complete type."""
        return self.n is not None

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

    """

    def __init__(self, args, ret):
        """Initialize type."""
        self.args = args
        self.ret = ret
        super().__init__(1)

    def compatible(self, other):
        """Return True iff other is a compatible type to self."""

        # TODO: This is not implemented correctly. Function pointer
        # compatibility rules are confusing.

        if not other.is_function():
            return False
        elif len(self.args) != len(other.args):
            return False
        elif any(not a1.compatible(a2) for a1, a2 in
                 zip(self.args, other.args)):
            return False
        elif not self.ret.compatible(other.ret):
            return False

        return True

    def is_complete(self):
        return False

    def is_function(self):
        """Check if this is a function type."""
        return True


class StructCType(CType):
    """Represents a struct ctype.

    tag - Name of the struct as a string, or None if it's anonymous
    members - List of members of the struct. Each element of the list should be
    a tuple (str, ctype) where `str` is the string of the identifier used to
    access that member and ctype is the ctype of that member.
    complete - Boolean indicating whether this struct is complete
    """

    def __init__(self, tag, members=None):
        self.tag = tag
        self.members = members
        super().__init__(1)

    def compatible(self, other):
        """Return True iff other is a compatible type to self.

        Within a single translation unit, two structs are compatible iff
        they are the exact same declaration.
        """
        return self is other

    def is_complete(self):
        """Check whether this is a complete type."""
        return self.members is not None

    def is_object(self):
        """Check whether this is an object type."""
        return True

    def set_members(self, members):
        """Add the given members to this struct and set it to complete."""
        self.members = members
        self.size = sum(m[1].size for m in members)


void = VoidCType()

# In our implementation, we have 1 represent true and 0 represent false. We
# maintain this convention so that true boolean values always compare equal.
bool_t = IntegerCType(1, False)

char = IntegerCType(1, True)
unsig_char = IntegerCType(1, False)

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


# When adding new types, update this function!
def to_unsigned(ctype):
    """Convert the given ctype from above to the unsigned version."""
    unsig_map = {char: unsig_char,
                 short: unsig_short,
                 integer: unsig_int,
                 longint: unsig_longint}
    return unsig_map[ctype]
