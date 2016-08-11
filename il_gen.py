"""Utilities for the AST -> IL phase of the compiler. 
"""

class CType:
    """Represents a C type, like int or double or a struct.
    
    size (int) - the result of sizeof of this type
    """
    def __init__(self, size):
        self.size = size
    
class ILCode:
    """Stores the IL code generated from the AST.
    
    lines (List) - the lines of code recorded
    """
    def __init__(self):
        self.lines = []

    # Supported commands:
    # Accepts one output argument and one input argument. Sets the output
    # argument to the input argument.
    SET = 1
    # Accepts one input argument. Returns the input argument value from the
    # current function.
    RETURN = 2
    # Accepts one output argument and two input arguments. Sets the output
    # argument to the sum of the input arguments.
    ADD = 3
    # Accepts one output argument and two input arguments. Sets the output
    # argument to the product of the input arguments.
    MULT = 4

    def add_command(self, command, arg1 = None, arg2 = None, output = None):
        """Add a new command to the IL code

        command (int) - One of the options above
        arg1, arg2, output (ILValue) - ILValue objects representing storage
        locations
        """
        self.lines.append((command, arg1, arg2, output))

    def __str__(self):
        def command_name(command):
            """Return the name of a command as a string:
            command_name(self.RETURN) -> "RETURN"

            This is a /terrible/ hack, but works for debugging purposes.
            """
            for name in ILCode.__dict__:
                if ILCode.__dict__[name] == command: return name.ljust(7)
            return None

        strlines = []
        for line in self.lines:
           strlines.append(str(line[3]) + " - " + command_name(line[0]) + " " +
                           str(line[1]) + ", " + str(line[2]))
        return '\n'.join(strlines)

    def __eq__(self, other):
        """Note that `other` need not use real ILValue objects as the command
        arguments. For testing, it can be easier to use integers or strings."""
        
        # keys are ILValue ids from self, and values are ILValue ids from other
        value_map = dict()

        def is_equivalent(value1, value2):
            """Check if ILValue value1 in self is equivalent to ILValue
            value2 in other based on the context so far
            """
            if value1 is None and value2 is None: return True
            elif value1 is None or value2 is None: return False
            
            if value1 in value_map:
                return value2 is value_map[value1]
            elif value2 in value_map.values():
                return False
            else:
                value_map[value1] = value2
                return True
        
        # Check if number of lines match
        if len(other.lines) != len(self.lines): return False
        for line1, line2 in zip(self.lines, other.lines):
            # Check if commands match
            if line1[0] != line2[0]: return False
            # Check if arguments match
            for i in range(1,4):
                if not is_equivalent(line1[i], line2[i]): return False
        return True

class ILValue:
    """Stores a value that appears as an element in generated IL code.

    ctype (Type) - the C type of this value
    """
    def __init__(self, ctype):
        self.ctype = ctype
    def __str__(self):
        """Pretty-print the last 4 digits of the ID for display.
        """
        return str(id(self) % 10000)

class LiteralILValue(ILValue):
    """Stores an ILValue that represents a literal value.
    
    value (str) - the value in an representation that is convenient for asm
    """
    def __init__(self, ctype, value):
        super().__init__(ctype)
        self.value = value

class VariableILValue(ILValue):
    """Stores an ILValue that represents a variable.

    offset (int) - the memory offset of this variable
    """
    def __init__(self, ctype, offset):
        super().__init__(ctype)
        self.offset = offset

class SymbolTable:
    """The symbol table for the AST -> IL phase. Stores variable name and types.
    Mostly used for type checking.
    """
    def __init__(self):
        self.table = dict()

    def lookup(self, name):
        """Look up the identifier with the given name and return its
        corresponding variable.

        name (str) - the identifier name to search for
        """
        if name in self.table:
            return self.table[name]
        else:
            # TODO: raise a real exception here
            raise NotImplementedError("unknown identifier")

    def add(self, name, ctype):
        """Add an identifier with the given name and type to the symbol table.

        name (str) - the identifier name to add
        ctype (CType) - the C type of the identifier we're adding
        """
        if name not in self.table:
            # TODO: use real offsets
            self.table[name] = VariableILValue(ctype, 0)
        else:
            # TODO: raise a real exception here
            raise NotImplementedError("already declared")
