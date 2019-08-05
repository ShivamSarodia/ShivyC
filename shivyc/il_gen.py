"""Objects used for the AST -> IL phase of the compiler."""

from collections import namedtuple
from copy import copy

from shivyc.ctypes import CType
import shivyc.il_cmds.control as control_cmds
from shivyc.errors import CompilerError


class ILCode:
    """Stores the IL code generated from the AST.

    commands - Dictionary mapping function name to list of IL commands for
    that function.
    cur_func (str) - Name of the function current commands are for
    label_num (int) - Unique identifier returned by get_label
    """
    def __init__(self):
        """Initialize IL code."""
        self.commands = {}
        self.cur_func = None

        self.label_num = 0

        self.static_inits = {}
        self.literals = {}
        self.string_literals = {}

    def copy(self):
        """Make copy of this object.

        Preserves identity of all ILValues stored within, but modifying the
        commands, literals, etc. in the returned object does not modify the
        original.
        """
        new = ILCode()
        new.commands = {name: self.commands[name].copy()
                        for name in self.commands}
        new.cur_func = self.cur_func
        self.label_num = self.label_num
        self.static_inits = self.static_inits.copy()
        self.literals = self.literals.copy()
        self.string_literals = self.string_literals.copy()
        return new

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

    def always_returns(self):
        """Return true if this function ends in a return command."""
        return (self.commands[self.cur_func] and
                isinstance(self.commands[self.cur_func][-1],
                           control_cmds.Return))

    def register_literal_var(self, il_value, value):
        """Register a literal IL value.

        il_value - ILValue object that has a literal value
        value - Literal value to store in the ILValue
        """
        il_value.literal = IntegerLiteral(value)
        self.literals[il_value] = value

    def register_string_literal(self, il_value, chars):
        """Register a string literal IL value.

        chars (List(int)) - Null-terminated list of character ASCII codes in
        the string.

        """
        il_value.literal = StringLiteral(chars)
        self.string_literals[il_value] = chars

    def static_initialize(self, il_value, init_val):
        """Initialize given value statically before program execution begins.

        il_value - ILValue object to initialize
        init_val - Numeric value to initialize `il_value` to
        """
        self.static_inits[il_value] = init_val

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
    literal_val - the value of this IL value if it represents a literal
    value. Do not set this value directly; it is set by the
    ILCode.register_literal_var function.
    """

    def __init__(self, ctype):
        """Initialize IL value."""
        self.ctype = ctype
        self.literal = None

    def __str__(self):  # pragma: no cover
        return f'{id(self) % 1000:03}'

    def __repr__(self):  # pragma: no cover
        return str(self)


class _Literal:
    """Base class for integer literals, string literals, etc."""
    def __init__(self, val):
        self.val = val


class IntegerLiteral(_Literal):
    """Class for integer literals."""
    def __init__(self, val):
        super().__init__(int(val))


class StringLiteral(_Literal):
    """Class for string literals."""
    def __init__(self, val):
        super().__init__(str(val))


class SymbolTable:
    """Symbol table for the IL -> AST phase.

    This object stores variable names, types, typedefs, and maintains
    information on the variable linkages and storage durations.
    """
    Tables = namedtuple('Tables', ['vars', 'structs'])

    # Definition statuses
    UNDEFINED = 1
    TENTATIVE = 2
    DEFINED = 3

    # Linkages
    INTERNAL = 1
    EXTERNAL = 2

    # Storage durations
    STATIC = 1
    AUTOMATIC = 2

    def __init__(self):
        """Initialize symbol table.

        `tables` is a list of namedtuples of dictionaries. Each dictionary
        in the namedtuple is the symbol table for a different namespace.

        """
        self.tables = []

        # Store variable linkages
        # ILValue -> INTERNAL / EXTERNAL
        self.linkage_type = {}

        # INTERNAL/EXTERNAL -> name -> ILValue
        self.linkages = {self.INTERNAL: {}, self.EXTERNAL: {}}

        # Store variable definition states
        # ILValue -> DEFINED/UNDEFINED/TENTATIVE
        self.def_state = {}

        # Store variable storage durations
        # ILValue -> STATIC/AUTOMATIC/None
        self.storage = {}

        # Store the names of all IL values.
        # ILValue -> name
        self.names = {}

        self.new_scope()

    def new_scope(self):
        """Initialize a new scope for the symbol table."""
        self.tables.append(self.Tables(dict(), dict()))

    def end_scope(self):
        """End the most recently started scope."""
        self.tables.pop()

    def _lookup_raw(self, name):
        """Look up the identifier or ctype with the given name.

        This function returns None if not found.

        name (str) - Identifier name to search for.
        """
        for table, _ in self.tables[::-1]:
            if name in table:
                return table[name]

    def lookup_variable(self, identifier):
        """Look up the given identifier.

        This function returns the ILValue object for the identifier, or raises
        an exception if not found or if the identifier is a typedef.

        identifier (Token(Identifier)) - Identifier to look up
        """
        ret = self._lookup_raw(identifier.content)

        if ret and isinstance(ret, ILValue):
            return ret
        else:
            descrip = f"use of undeclared identifier '{identifier.content}'"
            raise CompilerError(descrip, identifier.r)

    def lookup_linkage(self, identifier):
        """Return the linkage of identifier.

        If identifier doesn't exist or has no linkage, returns None.
        """
        return self.linkage_type.get(self._lookup_raw(identifier.content))

    def add_variable(self, identifier, ctype, defined, linkage, storage):
        """Add an identifier with the given name and type to the symbol table.

        identifier (Token) - Identifier to add, for error purposes.
        ctype (CType) - C type of the identifier we're adding.
        defined - one of DEFINED, UNDEFINED, or TENTATIVE
        linkage - one of INTERNAL, EXTERNAL, or None
        storage - STATIC, AUTOMATIC, or None

        return (ILValue) - the ILValue added
        """
        name = identifier.content

        # if it's already declared in this scope
        if name in self.tables[-1].vars:
            var = self.tables[-1].vars[name]
            if isinstance(var, CType):
                err = f"redeclared type definition '{name}' as variable"
                raise CompilerError(err, identifier.r)
            if defined == self.def_state[var] == self.DEFINED:
                raise CompilerError(f"redefinition of '{name}'", identifier.r)
            if linkage != self.linkage_type.get(var, None):
                err = f"redeclared '{name}' with different linkage"
                raise CompilerError(err, identifier.r)
        elif linkage and name in self.linkages[linkage]:
            var = self.linkages[linkage][name]
        else:
            var = ILValue(ctype)

        # Verify new type is compatible with previous type (if there was one)
        if not var.ctype.compatible(ctype):
            err = f"redeclared '{name}' with incompatible type"
            raise CompilerError(err, identifier.r)
        else:
            # Update type of stored variable (in case this declaration
            # completed an object type)
            var.ctype = ctype

        self.tables[-1].vars[name] = var

        # Set this variable's linkage if it has one
        if linkage:
            self.linkages[linkage][name] = var
            self.linkage_type[var] = linkage

        self.def_state[var] = max(self.def_state.get(var, 0), defined)

        # If this variable has not been assigned a storage duration, or the
        # previous storage duration was None, assign it this storage duration.
        if not self.storage.get(var, None):
            self.storage[var] = storage

        self.names[var] = name
        return var

    def lookup_struct_union(self, tag):
        """Looks up for struct or union by tag name and returns
        its ctype object.

        If not found, returns None.
        """
        for _, structs in self.tables[::-1]:
            if tag in structs: return structs[tag]

    def add_struct_union(self, tag, ctype):
        """Add struct or union to the symbol table and return it.

        If struct or union already exists in the topmost scope, this function
        does not modify the symbol table and just returns the existing ctype.
        Otherwise, this function adds this type to the topmost scope and
        returns it.
        """
        if tag not in self.tables[-1].structs:
            self.tables[-1].structs[tag] = ctype

        return self.tables[-1].structs[tag]

    def add_typedef(self, identifier, ctype):
        """Add a type definition to the symbol table."""

        name = identifier.content
        if name in self.tables[-1].vars:
            old_ctype = self.tables[-1].vars[name]
            if isinstance(old_ctype, ILValue):
                err = f"'{name}' redeclared as type definition in same scope"
                raise CompilerError(err, identifier.r)
            elif not old_ctype.compatible(ctype):
                err = f"'{name}' redeclared as incompatible type in same scope"
                raise CompilerError(err, identifier.r)
            else:
                return

        self.tables[-1].vars[name] = ctype

    def lookup_typedef(self, identifier):
        """Look up a typedef from the symbol table.

        If not found, raises an exception.
        """
        ctype = self._lookup_raw(identifier.content)
        if isinstance(ctype, CType):
            return ctype
        else:
            # This exception is only raised when the parser symbol table
            # makes an error, and this only happens when there is another
            # error in the source anyway. For example, consider this:
            #
            # int A;
            # {
            #   static typedef int A;
            #   A a;
            # }
            #
            # The parser symbol table will naively think that A is a
            # typedef on the line `A a`, when in fact the IL gen step will
            # still classify it as an integer because the `static
            # typedef int A;` is not a valid declaration. In this case,
            # we raise the error below.
            err = f"use of undeclared type definition '{identifier.content}'"
            raise CompilerError(err, identifier.r)


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
        self.return_type = None
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

    def set_return(self, ctype):
        """Return copy of self with return_type set to given value."""
        c = copy(self)
        c.return_type = ctype
        return c
