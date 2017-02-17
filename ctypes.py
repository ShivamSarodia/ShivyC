"""All of the C types recognized by the compiler."""

from il_gen import CType

# In our implementation, we have 1 represent true and 0 represent false. We
# maintain this convention so that true boolean values always comare equal.
bool_t = CType(1, False)

char = CType(1, True)
unsig_char = CType(1, False)

short = CType(2, True)
unsig_short = CType(2, False)

integer = CType(4, True)
unsig_int = CType(4, False)

longint = CType(8, True)
unsig_longint = CType(8, False)


# When adding new types, update this function!
def to_unsigned(ctype):
    """Convert the given ctype from above to the unsigned version."""
    unsig_map = {char: unsig_char,
                 short: unsig_short,
                 integer: unsig_int,
                 longint: unsig_longint}
    return unsig_map[ctype]
