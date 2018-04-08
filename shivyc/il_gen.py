"""Objects used for the AST -> IL phase of the compiler."""

from collections import namedtuple
from copy import copy
from shivyc.errors import CompilerError


class ILCode:
    """Stores the IL code generated from the AST.

    commands - Dictionary mapping function name to list of IL commands for
    that function.
    label_num (int) - Unique identifier returned by get_label
    automatic_storage - Dictionary mapping IL value to name for the
    variables that have storage type automatic.
    static_storage - Like automatic_storage, but for storage type static.
    no_storage - Like automatic_storage, but for values that do not need
    storage.
    external - Dictionary mapping IL value to name for variables that have
    external linkage.

    """
    STATIC = 1
    AUTOMATIC = 2

    def __init__(self):
        """Initialize IL code."""
        self.commands = {}
        self.cur_func = None

        self.label_num = 0

        self.automatic_storage = {}
        self.static_storage = {}
        self.no_storage = {}

        self.external = {}

        self.literals = {}
        self.string_literals = {}

    def start_func(self, func):
        """Start a new function in the IL code.

        Call start_func before generating code for a new function.
        """
        self.cur_func = func
        self.commands[func] = []

    def add(self, command):
        """Add a new command to the IL code.

        command (ILCommand) - command to be added

        """
        self.commands[self.cur_func].append(command)

    def register_storage(self, il_value, storage, name):
        """Register the storage duration of this IL value.

        Using this function, register every non-free variable. For example,
        most local variables should be registered with AUTOMATIC storage
        duration, and static variables should be registered with STATIC
        storage duration.

        In addition, it is important that variables that do not need to be
        allocated storage be registered with storage of None. For example,
        functions and values that are declared as extern fall into this
        category.

        This function may be called multiple times on the same IL value. If
        one of the calls gives it a storage of ILCode.AUTOMATIC or
        ILCode.STATIC, that storage is preserved and any calls that give it
        a storage of None are wiped.
        """
        if (not storage and il_value not in self.automatic_storage
              and il_value not in self.static_storage):
            self.no_storage[il_value] = name
        elif storage == ILCode.AUTOMATIC:
            self.automatic_storage[il_value] = name
        elif storage == ILCode.STATIC:
            self.static_storage[il_value] = name

    def register_extern_linkage(self, il_value, name):
        """Register this IL value as having external linkage.

        If this IL value is defined in this translation unit, it will be made
        available globally in the generated assembly code.
        """
        self.external[il_value] = name

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
        return f'{id(self) % 1000:03}'

    def __repr__(self):  # pragma: no cover
        return str(self)


class SymbolTable:
    """Symbol table for the IL -> AST phase.

    This object stores variable name and types, and is mostly used for type
    checking.

    """
    Tables = namedtuple('Tables', ['vars', 'structs'])
    Variable = namedtuple("Variable", ['il_value', 'linkage', 'defined'])

    INTERNAL = 1
    EXTERNAL = 2

    def __init__(self):
        """Initialize symbol table.

        `tables` is a list of namedtuples of dictionaries. Each dictionary
        in the namedtuple is the symbol table for a different namespace.

        `internal` and `external` are dictionaries mapping an identifier (
        string) to IL values. `internal` is used for all IL values with
        internal linkage, and `external` is used for all IL values with
        external linkage.
        """
        self.tables = []
        self.internal = {}
        self.external = {}
        self.new_scope()

    def new_scope(self):
        """Initialize a new scope for the symbol table."""
        self.tables.append(self.Tables(dict(), dict()))

    def end_scope(self):
        """End the most recently started scope."""
        self.tables.pop()

    def lookup_raw(self, name):
        """Look up the variable identifier with the given name.

        This function returns the Variable object for the identifier,
        or None if not found.

        Callers should prefer the function lookup_tok over this function,
        because the Variable object definition is subject to change.

        name (str) - Identifier name to search for.

        """
        for table, _ in self.tables[::-1]:
            if name in table:
                return table[name]

    def lookup_tok(self, identifier):
        """Look up the given identifier.

        This function returns the ILValue object for the identifier, or raises
        an exception if not found.

        identifier (Token(Identifier)) - Identifier to look up

        """
        ret = self.lookup_raw(identifier.content)
        if ret:
            return ret.il_value
        else:
            descrip = f"use of undeclared identifier '{identifier.content}'"
            raise CompilerError(descrip, identifier.r)

    def add(self, identifier, ctype, defined, linkage):
        """Add an identifier with the given name and type to the symbol table.

        identifier (Token) - Identifier to add, for error purposes.
        ctype (CType) - C type of the identifier we're adding.
        defined (bool) - Whether this identifier was defined (or declared)
        linkage - one of INTERNAL, EXTERNAL, or None
        return (ILValue) - the ILValue added
        """
        name = identifier.content

        # if it's already declared in this scope
        if name in self.tables[-1].vars:
            var = self.tables[-1].vars[name]
            if defined and var.defined:
                raise CompilerError(f"redefinition of '{name}'", identifier.r)
            if linkage != var.linkage:
                err = f"redeclared '{name}' with different linkage"
                raise CompilerError(err, identifier.r)
        elif linkage == self.INTERNAL and name in self.internal:
            var = self.Variable(self.internal[name], linkage, defined)
        elif linkage == self.EXTERNAL and name in self.external:
            var = self.Variable(self.external[name], linkage, defined)
        else:
            var = self.Variable(ILValue(ctype), linkage, defined)

        self.tables[-1].vars[name] = var
        if linkage == self.INTERNAL:
            self.internal[name] = var.il_value
        elif linkage == self.EXTERNAL:
            self.external[name] = var.il_value

        # Verify the type is compatible with the previous type
        if not var.il_value.ctype.compatible(ctype):
            err = f"redeclared '{name}' with incompatible type"
            raise CompilerError(err, identifier.r)

        return var.il_value

    def lookup_struct(self, tag):
        """Look up struct by tag name and return its ctype object.

        If not found, returns None.
        """
        for _, structs in self.tables[::-1]:
            if tag in structs: return structs[tag]

    def add_struct(self, tag, ctype):
        """Add struct to the symbol table and return it.

        If struct already exists in the topmost scope, this function does
        not modify the symbol table and just returns the existing struct
        ctype. Otherwise, this function adds this struct to the topmost
        scope and returns it.
        """
        if tag not in self.tables[-1].structs:
            self.tables[-1].structs[tag] = ctype

        return self.tables[-1].structs[tag]


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

    def set_break(self, lab):
        """Return copy of self with break_label set to given value."""
        c = copy(self)
        c.break_label = lab
        return c

    def set_continue(self, lab):
        """Return copy of self with break_label set to given value."""
        c = copy(self)
        c.continue_label = lab
        return c
