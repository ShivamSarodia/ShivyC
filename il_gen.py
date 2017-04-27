"""Objects used for the AST -> IL phase of the compiler."""

import ctypes
from ctypes import PointerCType
from errors import CompilerError, error_collector


class ILCode:
    """Stores the IL code generated from the AST.

    commands (List) - The commands recorded.
    label_num (int) - Unique identifier returned by get_label
    externs (List(str)) - List of external identifiers in code
    literals (Dict(ILValue -> str)) - Mapping from ILValue to the literal
    value it represents
    variables (Dict(ILValue -> str or None)) - Mapping from ILValue to None
    if it is on stack, else its label in ASM.

    """

    def __init__(self):
        """Initialize IL code."""
        self.commands = []
        self.label_num = 0

        self.variables = []
        self.externs = {}
        self.literals = {}
        self.string_literals = {}

    def add(self, command):
        """Add a new command to the IL code.

        command (ILCommand) - command to be added

        """
        self.commands.append(command)

    def register_local_var(self, il_value):
        """Add a stack variable.

        Using this function, register every variable which needs local stack
        allocation. Note that while variables registered with this function
        are called "stack variables" above, the register allocator may opt
        to place them in registers if appropriate.

        il_value - ILValue to register as a variable
        """
        if il_value not in self.variables:
            self.variables.append(il_value)

    def register_extern_var(self, il_value, name):
        """Register an extern variable.

        Using this function, register every extern variable. Do not also
        call register_local_var on this ILValue.

        il_value (ILValue) - IL value to register as an extern variable
        name (str) - name of the extern variable
        """
        self.externs[il_value] = name

    def register_literal_var(self, il_value, value):
        """Register a literal IL value.

        il_value - ILValue object that has a literal value
        value - Literal value to store in the ILValue
        """
        self.literals[il_value] = value

    def register_string_literal(self, il_value, chars):
        """Register a string literal IL value.

        chars (List(int)) - Null-terminated list of character ASCII codes in
        the string.

        """
        self.string_literals[il_value] = chars

    def get_label(self):
        """Return a unique label identifier string."""
        # Kind of hacky. Ideally, we would return labels here that were unique
        # to the ILCode, and then when generating the ASM code, assign each
        # ILCode label to an ASM code label.

        # Import is here to prevent circular import.
        from asm_gen import ASMCode
        return ASMCode.get_label()

    def __str__(self):  # pragma: no cover
        return "\n".join(str(command) for command in self.commands)

    def __iter__(self):
        """Return the lines of code in order when iterating through ILCode.

        The returned lines will have command, arg1, arg2, and output as
        attributes, some of which may be NONE if not applicable for that
        command.

        """
        return iter(self.commands)

    def __eq__(self, other):  # pragma: no cover
        """Check for equality between this IL code object and another.

        Equality is only checked by verifying the IL commands are correct! The
        arguments are currently not examined. This is a very weak form of
        equality checking, and could perhaps be improved.

        """
        if len(self.commands) != len(other.commands):
            return False
        return all(c1 == c2 for c1, c2 in zip(self.commands, other.commands))


class ILValue:
    """Value that appears as an element in generated IL code.

    ctype (CType) - C type of this value.

    """

    def __init__(self, ctype, null_ptr_const=False):
        """Initialize IL value.

        ctype (CType) - type of this ILValue
        null_ptr_const (Bool) - True iff this represents a null pointer
        constant. Used for some pointer operations, because a null pointer
        constant is valid in many pointer spots.
        """
        self.ctype = ctype
        self.null_ptr_const = null_ptr_const

    def __str__(self):  # pragma: no cover
        return str(id(self) % 1000).zfill(3)

    def __repr__(self):  # pragma: no cover
        return str(self)


class LValue:
    """Represents an LValue.

    There are two types of LValues, a direct LValue and indirect LValue. A
    direct LValue stores an ILValue to which this LValue refers. An indirect
    LValue stores an ILValue which points to the object this ILValue refers
    to.

    Note this is not directly related to the ILValue class above.

    lvalue_type (DIRECT or INDIRECT) - See description above.
    il_value (ILValue) - ILValue describing this lvalue. If this is an
    indirect lvalue, the il_value will have pointer type.
    """

    DIRECT = 0
    INDIRECT = 1

    def __init__(self, lvalue_type, il_value):
        """Initialize LValue."""
        self.lvalue_type = lvalue_type
        self.il_value = il_value

    def modable(self):
        """Return whether this is a modifiable lvalue."""
        if self.lvalue_type == self.DIRECT:
            ctype = self.il_value.ctype
        else:  # self.lvalue_type == self.INDIRECT
            ctype = self.il_value.ctype.arg

        return ctype.is_arith() or ctype.is_pointer()

    def set_to(self, rvalue, il_code, r):
        """Emit code to set the given lvalue to the given ILValue.

        rvalue (ILValue) - rvalue to set this lvalue to
        il_code (ILCode) - ILCode object to add generated code
        r (Range) - Range for warning/error messages
        return - ILValue representing the result of this operation

        """
        # Import must be local to avoid circular imports
        import il_commands

        if self.lvalue_type == self.DIRECT:
            check_cast(rvalue, self.il_value.ctype, r)
            return set_type(rvalue, self.il_value.ctype,
                            il_code, self.il_value)
        elif self.lvalue_type == self.INDIRECT:
            check_cast(rvalue, self.il_value.ctype.arg, r)
            right_cast = set_type(rvalue, self.il_value.ctype.arg, il_code)
            il_code.add(il_commands.SetAt(self.il_value, right_cast))
            return right_cast

    def addr(self, il_code):
        """Generate code for and return address of this lvalue."""

        # Import must be local to avoid circular dependencies
        import il_commands

        if self.lvalue_type == self.DIRECT:
            out = ILValue(PointerCType(self.il_value.ctype))
            il_code.add(il_commands.AddrOf(out, self.il_value))
            return out
        else:
            return self.il_value

    def ctype(self):
        """Return the ctype of this lvalue."""

        if self.lvalue_type == self.DIRECT:
            return self.il_value.ctype
        else:
            return self.il_value.ctype.arg


class SymbolTable:
    """Symbol table for the IL -> AST phase.

    This object stores variable name and types, and is mostly used for type
    checking.

    """

    def __init__(self):
        """Initialize symbol table."""
        self.tables = [dict()]

    def new_scope(self):
        """Initialize a new scope for the symbol table."""
        self.tables.append(dict())

    def end_scope(self):
        """End the most recently started scope."""
        self.tables.pop()

    def lookup(self, name):
        """Look up the identifier with the given name.

        This function returns the ILValue object for the identifier, or None if
        not found.

        name (str) - Identifier name to search for.

        """
        for table in self.tables:
            if name in table: return table[name]

    def lookup_tok(self, identifier):
        """Look up the given identifier.

        This function returns the ILValue object for the identifier, or raises
        an exception if not found.

        identifier (Token(Identifier)) - Identifier to look up

        """
        ret = self.lookup(identifier.content)
        if ret:
            return ret
        else:
            descrip = "use of undeclared identifier '{}'"
            raise CompilerError(
                descrip.format(identifier.content), identifier.r)

    def add(self, identifier, ctype):
        """Add an identifier with the given name and type to the symbol table.

        identifier (Token) - Identifier to add, for error purposes.
        ctype (CType) - C type of the identifier we're adding.
        return (ILValue) - the ILValue added
        """
        name = identifier.content
        if name not in self.tables[-1]:
            il_value = ILValue(ctype)
            self.tables[-1][name] = il_value
            return il_value
        else:
            descrip = "redefinition of '{}'"
            raise CompilerError(descrip.format(name), identifier.r)


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
            descrip = "conversion from incompatible pointer type"
            error_collector.add(CompilerError(descrip, range, True))
            return

    # Cast from null pointer constant to pointer okay
    elif ctype.is_pointer() and il_value.null_ptr_const:
        return

    # Cast from pointer to boolean okay
    elif ctype == ctypes.bool_t and il_value.ctype.is_pointer():
        return

    else:
        descrip = "invalid conversion between types"
        raise CompilerError(descrip, range)


def set_type(il_value, ctype, il_code, output=None):
    """If necessary, emit code to cast given il_value to the given ctype.

    This function does no type checking and will never produce a warning or
    error.

    """
    # Import must be local to avoid circular imports
    import il_commands

    # (no output value, and same types) OR (output is same as input)
    if (not output and il_value.ctype == ctype) or output == il_value:
        return il_value
    else:
        if not output:
            output = ILValue(ctype)
        il_code.add(il_commands.Set(output, il_value))
        return output
