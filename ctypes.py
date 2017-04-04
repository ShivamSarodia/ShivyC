"""All of the C types recognized by the compiler."""

import token_kinds
from il_gen import VoidCType, IntegerCType

void = VoidCType()

# In our implementation, we have 1 represent true and 0 represent false. We
# maintain this convention so that true boolean values always comare equal.
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
