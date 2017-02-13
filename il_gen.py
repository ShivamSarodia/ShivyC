"""Objects used for the AST -> IL phase of the compiler."""

from errors import CompilerError


class CType:
    """Represents a C type, like `int` or `double` or a struct.

    size (int) - The result of sizeof on this type.
    signed (bool) - Whether this type is signed.

    """

    def __init__(self, size, signed):
        """Initialize type."""
        self.size = size
        self.signed = signed


class ILCode:
    """Stores the IL code generated from the AST.

    commands (List) - The commands recorded.
    label_num (int) - Unique identifier returned by get_label

    """

    def __init__(self):
        """Initialize IL code."""
        self.commands = []
        self.label_num = 0

    def add(self, command):
        """Add a new command to the IL code.

        command (ILCommand) - command to be added

        """
        self.commands.append(command)

    def get_label(self):
        """Return a unique label identifier."""
        self.label_num += 1
        return self.label_num

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

    Do not use this class directly; instead, use one of the derived classes
    below.

    value_type (enum) - One of the values below describing the general
    type of value this is.
    ctype (Type) - C type of this value.

    """

    # Options for value_type:
    # Temporary value. These are used to store intermediate values in
    # computations.
    TEMP = 1
    # Literal value. These are literal values that are known at compile time.
    LITERAL = 2
    # Variable value. These represent variables in the original C code.
    VARIABLE = 3

    def __init__(self, value_type, ctype):
        """Initialize IL value."""
        self.ctype = ctype
        self.value_type = value_type

    def __str__(self):
        """Pretty-print the last 4 digits of the ID for display."""
        return str(id(self) % 10000)


class TempILValue(ILValue):
    """ILValue that represents a temporary intermediate value."""

    def __init__(self, ctype):
        """Initialize temp IL value."""
        super().__init__(ILValue.TEMP, ctype)


class LiteralILValue(ILValue):
    """ILValue that represents a literal value.

    value (str) - Value in an representation that is convenient for asm.

    """

    def __init__(self, ctype, value):
        """Initialize literal IL value."""
        super().__init__(ILValue.LITERAL, ctype)
        self.value = value

    # We want to literals to compare equal iff they have the same value and
    # type, so the ASM generation step can keep track of their storage
    # locations as one unit.
    def __eq__(self, other):
        """Test equality by comparing type and value."""
        if not isinstance(other, LiteralILValue):
            return False
        return self.ctype == other.ctype and self.value == other.value

    def __hash__(self):
        """Hash based on type and value."""
        return hash((self.ctype, self.value))


class VariableILValue(ILValue):
    """ILValue that represents a variable.

    offset (int) - Memory offset of this variable, usually positive.

    """

    # TODO: why does this have an offset? shouldn't offset be ASM specific?

    def __init__(self, ctype, offset):
        """Initialize variable IL value."""
        super().__init__(ILValue.VARIABLE, ctype)
        self.offset = offset


class SymbolTable:
    """Symbol table for the IL -> AST phase.

    This object stores variable name and types, and is mostly used for type
    checking.

    """

    def __init__(self):
        """Initialize symbol table."""
        self.table = dict()

    def lookup(self, name):
        """Look up the identifier with the given name.

        This function returns the ILValue object for the identifier, or None if
        not found.

        name (str) - Identifier name to search for.

        """
        if name in self.table:
            return self.table[name]
        else:
            return None

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

    def add(self, name, ctype):
        """Add an identifier with the given name and type to the symbol table.

        name (str) - Identifier name to add.
        ctype (CType) - C type of the identifier we're adding.

        """
        if name not in self.table:
            # TODO: use real offsets
            self.table[name] = VariableILValue(ctype, 0)
        else:
            # TODO: raise a real exception here
            raise NotImplementedError("already declared")
