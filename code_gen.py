"""Defines the classes necessary for the code generation step of the compiler.

"""
from collections import OrderedDict
from contextlib import contextmanager

from errors import CompilerError
import errors

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
        header = ["global main"]
        return "\n".join(header + [to_string(line) for line in self.lines])

class SymbolState:
    """Stores the symbol table and other details about the compiler state that
    should must be carried throughout the tree as code is generated.

    symbol_tables (List[Dict(str, ValueInfo)]) - Stores a list of symbol
    tables, where the last is the most local symbol table and the first is the
    most global. Each symbol table is a dictionary mapping identifier names to 
    a ValueInfo object with information on where in memory this object is
    stored.

    next_free (int) - The next location on stack, measured in bytes below RBP,
    that currently has no variable occupying that space.

    stack_shift (int) - Stores how much the RSP has been moved since the
    beginning of the function call, so we know how much to move the RSP back
    before returning. This is an upper bound on the amount of space required
    on the stack to store all variables declared in the current function and
    should round up to a multiple of 16.

    register_state (OrderedDict) - Stores each register name in order of
    preference with value True if available or False if checked out

    """
    def __init__(self):
        self.symbol_tables = []
        self.next_free = 8
        self.stack_shift = 0

        self.register_state = OrderedDict([("eax", True), ("edi", True)])
    
    @contextmanager
    def new_symbol_table(self):
        """Defines a context manager for a new symbol table. That is:

        with code_store.new_symbol_table():
            do stuff

        This will automatically push a new symbol table before "do stuff" and
        pop it afterwards.

        """
        # We save the current value of self.next_free because after this symbol
        # table is popped off, we must reset self.next_free to its previous
        # value.
        next_free = self.next_free
        self.symbol_tables.append(dict())
        yield
        self.symbol_tables.pop()
        self.next_free = next_free

    def add_symbol(self, identifier, ctype):
        """Add a symbol to the topmost symbol table. Returns False if variable
        was already defined.

        identifier (str) - the variable name
        ctype (Type) - the type of this variable
        returns - True if it is OK, False if the variable was already defined or
        declared with a different type
        
        """
        # TODO: support variables that have been declared but not defined
        if identifier in self.symbol_tables[-1]:
            return False
        else:
            self.symbol_tables[-1][identifier] = ValueInfo(ctype,
                                                           ValueInfo.STACK,
                                                           self.next_free)
            self.next_free += ctype.size
            return True

    def get_symbol(self, identifier):
        """Gets a symbol from the symbol tables, starting search from the most
        local and proceeding to the most global. Returns the corresponding 
        ValueInfo object for the identifier a match is found, or None otherwise.
        Guarantees that the returned ValueInfo object has storage_type STACK.

        identifier (str) - the identifier to search for
        returns (ValueInfo) - object containing storage location of returned
        value
        """
        for table in self.symbol_tables[::-1]:
            if identifier in table: return table[identifier]
        return None

    def get_symbol_or_error(self, identifier_token):
        """Similar to get_symbol, but raises an exception if the symbol is not
        found.

        identifier_token (Token(identifier)) - the identifier to search for"""
        value = self.get_symbol(identifier_token.content)
        if value: return value
        if not value:
            raise errors.token_error("undeclared identifier '{}'",
                                     identifier_token)

    # When a caller calls checkout_reg, it is guaranteed that the register
    # returned will not be visibly modified by any other call to make_code. That
    # is, the caller can assume that if a value is saved to a checked-out
    # register, that value will still be there after any calls to make_code.
    # Note that calls to make_code may temporarily move around the value in the
    # register, as long as it is put back in place before the call returns.
    def checkout_reg(self):
        """Return the name of a register that is currently unused. See comment
        above for usage details.

        returns (str) - register name"""

        for register in self.register_state:
            if self.register_state[register]:
                self.register_state[register] = False
                return register
        raise NotImplementedError("Ran out of registers")
            
    def return_reg(self, register):
        """Indicate that the provided register is now unused. It is VERY
        IMPORTANT that this be called to free registers once they are done being
        used, or subtle bugs may arise in long programs.

        """
        self.register_state[register] = True

class ASTData:
    """Every node in the AST stores an instance of the ASTData class. This class
    is useful for recording information about the tree so the entire tree need
    not be traversed to get information about the program. For example, the
    code generation step needs to know the total amount of memory required by
    local declarations in a function before generating any function code. By
    storing in each node the total amount of memory required by local
    declarations in the subtree rooted at that node, we can easily calculate the
    total.

    stack_space_required (int) - Stores the total amount of stack space required
    by all declarations in this subtree

    """
    def __init__(self, stack_space_required = 0):
        self.stack_space_required = stack_space_required

    def __add__(self, other):
        return ASTData(
            stack_space_required=(self.stack_space_required
                                  + other.stack_space_required))
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

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
    storage_info (many types) - See comments on each value of storage_type enum

    """
    # Options for storage_type:

    # A literal value. Not actually stored in the compiled code, simply
    # remembered by the compiler because it appeared as a literal in the
    # provided source. The storage_info is a string representing the value.
    LITERAL = 1
    # A value stored on the stack. storage_info is an integer representing the
    # first (lowermost, closest to RBP) position in the stack containing this
    # object.
    STACK = 2
    # A value stored in a register. storage_info is the name of the register.
    REGISTER = 3
    
    def __init__(self, value_type, storage_type, storage_info):
        self.value_type = value_type
        self.storage_type = storage_type
        self.storage_info = storage_info

    def has_types(self, value_type, storage_type):
        return (value_type == self.value_type
                and storage_type == self.storage_type)

    def __str__(self):
        """Converts this ValueInfo storage_info into a form suitable for output
        asm"""
        if self.storage_type == self.STACK:
            return "DWORD [rbp-{}]".format(str(self.storage_info))
        else:
            return self.storage_info
