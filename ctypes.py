"""All of the C types recognized by the compiler."""

from il_gen import CType

# In this implementation, char is signed by default.
char = CType(1, True)
integer = CType(4, True)
