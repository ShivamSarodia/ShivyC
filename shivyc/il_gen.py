"""Objects used for the AST -> IL phase of the compiler."""

from copy import copy
from shivyc.errors import CompilerError


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
        from shivyc.asm_gen import ASMCode
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
        for table in self.tables[::-1]:
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


class Context:
    """Object for passing current context to make_il functions.

    break_label - Label to which a `break` statement in the current position
    would jump.
    continue_label - Label to which a `continue` statment in the current
    position would jump.
    is_global - Whether the current scope is global or within a function.
    Used by declarations to modify emitted code.
    """

    def __init__(self):
        """Initialize Context."""
        self.break_label = None
        self.continue_label = None
        self.is_global = False

    def set_global(self, val):
        """Return copy of self with is_global set to given value."""
        c = copy(self)
        c.is_global = val
        return c
