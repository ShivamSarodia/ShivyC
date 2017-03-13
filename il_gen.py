"""Objects used for the AST -> IL phase of the compiler."""

from errors import CompilerError


class CType:
    """Represents a C type, like `int` or `double` or a struct.

    size (int) - The result of sizeof on this type.

    """

    # Integer CType
    ARITH = 0
    # Function CTYPE
    FUNCTION = 1
    # Pointer CType
    POINTER = 2
    # Void CType
    VOID = 3

    def __init__(self, size, type_type):
        """Initialize type."""
        self.size = size
        self.type_type = type_type


class VoidCType(CType):
    """Represents a void C type."""

    def __init__(self):
        """Initialize type."""
        super().__init__(0, CType.VOID)

    def compatible(self, other):
        """Return True iff other is a compatible type to self."""
        return other.type_type == self.type_type


class IntegerCType(CType):
    """Represents an integer C type, like 'unsigned long' or 'bool'.

    size (int) - The result of sizeof on this type.
    signed (bool) - Whether this type is signed.

    """

    def __init__(self, size, signed):
        """Initialize type."""
        self.signed = signed
        super().__init__(size, CType.ARITH)

    def __str__(self):  # pragma: no cover
        return "({} INT {} BYTES)".format("SIG" if self.signed else "UNSIG",
                                            self.size)

    def compatible(self, other):
        """Return True iff other is a compatible type to self."""
        return (other.type_type == self.type_type and
                other.signed == self.signed and
                other.size == self.size)


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
        super().__init__(1, CType.FUNCTION)

    def __str__(self):  # pragma: no cover
        return "(FUNC RET {})".format(str(self.ret))

    def compatible(self, other):
        """Return True iff other is a compatible type to self."""
        raise NotImplementedError


class PointerCType(CType):
    """Represents a pointer C type.

    arg (CType) - Type pointed to.

    """

    def __init__(self, arg):
        """Initialize type."""
        self.arg = arg
        super().__init__(8, CType.POINTER)

    def __str__(self):  # pragma: no cover
        return "(PTR TO {})".format(str(self.arg))

    def compatible(self, other):
        """Return True iff other is a compatible type to self."""
        return (self.type_type == other.type_type and
                self.arg.compatible(other.arg))


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
        self.externs = []
        self.literals = {}
        self.variables = {}

    def add(self, command):
        """Add a new command to the IL code.

        command (ILCommand) - command to be added

        """
        self.commands.append(command)

    def add_extern(self, name):
        """Add a new extern name to the IL code. Passed on to generating ASM.

        name (str) - name to be added as extern

        """
        if name not in self.externs:
            self.externs.append(name)

    def add_literal(self, il_value, value):
        """Add a new literal to the IL code.

        il_value - ILValue object that has a literal value
        value - Literal value to store in the ILValue

        """
        self.literals[il_value] = value

    def add_variable(self, il_value, pos=None):
        """Add a variable, potentially with a preassigned position.

        il_value - ILValue to add
        pos - The preassigned place for this variable, or None otherwise.
        """
        self.variables[il_value] = pos

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
            raise CompilerError(descrip.format(identifier.content),
                                identifier.file_name,
                                identifier.line_num)

    def add(self, identifier, ctype, il_code):
        """Add an identifier with the given name and type to the symbol table.

        identifier (Token) - Identifier to add, for error purposes.
        ctype (CType) - C type of the identifier we're adding.

        """
        name = identifier.content
        if name not in self.tables[-1]:
            il_value = ILValue(ctype)
            il_code.add_variable(il_value)
            self.tables[-1][name] = il_value
        else:
            descrip = "redefinition of '{}'"
            raise CompilerError(descrip.format(name),
                                identifier.file_name,
                                identifier.line_num)
