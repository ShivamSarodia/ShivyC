"""Defines the classes necessary for the code generation step of the compiler.

"""
from contextlib import contextmanager

class CodeStore:
    """Stores the literal lines of asm code being generated.

    lines (List[Tuple, String]) - A list of the lines of code stored.  Commands
    are stored as tuples and labels are stored as strings without the
    terminating colon.

    """
    def __init__(self):
        self.lines = []

    def add_command(self, command):
        """Add a command to the code at current position

        command (tuple) - The command to add, split by spaces across a tuple
        e.g. ("mov", "rax", "rbx")

        """
        if not isinstance(command, tuple):
            raise ValueError("Command is not a tuple")
        self.lines.append(command)
        
    def add_label(self, label):
        """Add a label to the code at current position

        label (str) - The label name, without a colon

        """
        if not isinstance(label, str):
            raise ValueError("Label is not a string")
        self.lines.append(label)
        
    def full_code(self):
        """Return as a string the full assembly code generated.

        """
        def to_string(line):
            """Convert a single line from the `lines` variable into a string of
            asm code"""
            if isinstance(line, str):
                # It's a label
                return line + ":"
            else:
                # It's a command
                return "     " + line[0] + (" " + ", ".join(line[1:])
                                            if len(line) > 1 else "")
        
        # This code starts every asm program, so we put it here.
        header = ["global _start",
                  "",
                  "_start:",
                  "     call main",
                  "     mov rdi, rax",
                  "     mov rax, 60",
                  "     syscall"]
        return "\n".join(header + [to_string(line) for line in self.lines])

class SymbolState:
    """Stores the symbol table and other details about the compiler state that
    should must be carried throughout the tree as code is generated.

    symbol_tables (List[Dict(str, ValueInfo)]) - Stores a list of symbol
    tables, where the last is the most local symbol table and the first is the
    most global. Each symbol table is a dictionary mapping identifier names to 
    a ValueInfo object with information on where in memory this object is
    stored.

    """
    def __init__(self):
        self.symbol_tables = []
    
    @contextmanager
    def new_symbol_table(self):
        """Defines a context manager for a new symbol table. That is:

        with code_store.new_symbol_table():
            do stuff

        This will automatically push a new symbol table before "do stuff" and
        pop it afterwards.

        """
        symbol_tables.push_back(dict())
        yield
        symbol_tables.pop()

    def add_symbol(self, identifier, value_info):
        """Add a symbol to the topmost symbol table. Returns False if variable
        was already defined.

        identifier (str) - the variable name
        value_info (ValueInfo) - stores info about the value of this variable.
        (specifically, where on the stack it is stored)
        returns - True if it is OK, False if the variable was already defined or
        declared with a different type
        
        """
        # TODO: add in assertion that the ValueInfo object describes something
        # in memory
        # TODO: support variables that have been declared but not defined
        if identifier in self.symbol_tables[-1]:
            return False
        symbol_tables[-1][identifier] = value_info
        return True

    def get_symbol(self, identifier):
        """Gets a symbol from the symbol tables, starting search from the most
        local and proceeding to the most global. Returns the corresponding 
        ValueInfo object for the identifier a match is found, or None otherwise.
        """
        for table in symbol_tables[::-1]:
            if identifier in table: return table[identifier]
        return None

class Type:
    """Represents a C type, like 32-bit int, char, pointer to char, etc.
    
    size(int) - Size in bytes of this type in memory
    """
    def __init__(self, size):
        self.size = size
    
class ValueInfo:
    """Stores information about the type and storage location of an expression.

    value_type (Type) - The C type of the value
    storage_type (enum) - One of the provided enum values.
    storage_info (many types):
    1) If value_type is integer and storage_type is literal, then storage_info
       is a string of the integer value.

    """
    # Options for storage_type:

    # A literal value. Not actually stored in the compiled code, simply
    # remembered by the compiler because it appeared as a literal in the
    # provided source.
    LITERAL = 1

    def __init__(self, value_type, storage_type, storage_info):
        self.value_type = value_type
        self.storage_type = storage_type
        self.storage_info = storage_info
