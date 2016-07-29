"""Classes for the nodes that form our abstract syntax tree (AST). Each node
corresponds to a rule in the C grammar.

"""

from code_gen import ValueInfo
from tokens import Token
import ctypes
import token_kinds

class Node:
    """A general class for representing a single node in the AST. Inherit all
    AST nodes from this class. Every AST node also has a make_code function that
    accepts a code_store (CodeStore) to which the generated code should be saved
    and a symbol_state (SymbolState) that represents the compiler-internal state
    of symbols (e.g. the symbol table). Nodes representing expressions also
    return a ValueInfo object describing the generated value.

    symbol (str) - Each node must set the value of this class attribute to the
    non-terminal symbol the corresponding rule produces. This helps enforce tree
    structure so bugs in the parser do not accidentally slip into output code.

    """
    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def assert_symbol(self, node, symbol_name):
        """Useful for enforcing tree structure. Raises an exception if the
        node represents a rule that does not produce the expected symbol. 

        """
        if node.symbol != symbol_name:
            raise ValueError("malformed tree: expected symbol " + symbol_name +
                             ", got " + node.symbol)

    def assert_kind(self, token, kind):
        if token.kind != kind:
            raise ValueError("malformed tree: expected token kind " + str(kind) +
                             ", got " + str(token.kind))

class MainNode(Node):
    """ General rule for the main function. Will be removed once function
    definition is supported.
    
    statements (List[statement]) - a list of the statement in main function

    """
    symbol = "main_function"
    
    def __init__(self, block_items):
        super().__init__()

        # TODO(shivam): Add an assertion that all block_items are either a
        # statement or declaration.
        self.block_items = block_items
        
    def make_code(self, code_store, symbol_state):
        # Run through all declarations in this function and determine how much
        # stack space altogether is needed. We pre-allocate this much space on
        # the stack by moving the RSP, and restore it before returning from the
        # function.
        symbol_state.stack_space = 0
        for block_item in self.block_items:
            try: 
                symbol_state.stack_space += block_item.stack_space
            except AttributeError: pass

        # Align symbol_state.stack_space to be a multiple of 16 so the stack
        # frame is always aligned to a multiple of 16
        if symbol_state.stack_space % 16 != 0:
            symbol_state.stack_space += 16 - (symbol_state.stack_space % 16)
        
        with symbol_state.new_symbol_table():
            code_store.add_label("main")
            code_store.add_command(("push", "rbp"))
            code_store.add_command(("mov", "rbp", "rsp"))

            # Reserve the required amount of space on the stack
            if symbol_state.stack_space:
                code_store.add_command(("sub", "rsp",
                                        str(symbol_state.stack_space)))

            # Make the code for each item
            for block_item in self.block_items:
                block_item.make_code(code_store, symbol_state)

            # TODO: This is kind of hacky. Fix.
            # Return 0 at the end of the main function if nothing has been
            # returned yet.
            ReturnNode(NumberNode(Token(token_kinds.number, "0"))).make_code(
                code_store, symbol_state)

class ReturnNode(Node):
    """ Return statement

    return_value (expression) - value to return

    """
    symbol = "statement"

    def __init__(self, return_value):
        super().__init__()

        self.assert_symbol(return_value, "expression")
        self.return_value = return_value

    def make_code(self, code_store, symbol_state):
        value_info = self.return_value.make_code(code_store, symbol_state)
        if (value_info.value_type == ctypes.integer and
            value_info.storage_type == ValueInfo.LITERAL):
            code_store.add_command(("mov", "rax", value_info.storage_info))
        else:
            raise NotImplementedError

        # Move RSP back to where it was before the function executed
        if symbol_state.stack_space:
            code_store.add_command(("add", "rsp",
                                    str(symbol_state.stack_space)))
        code_store.add_command(("pop", "rbp"))
        code_store.add_command(("ret",))

        

class NumberNode(Node):
    """ Expression that is just a single number. 

    number (Token(Number)) - number this expression represents

    """
    symbol = "expression"
    
    def __init__(self, number):
        super().__init__()

        self.assert_kind(number, token_kinds.number)
        self.number = number

    def make_code(self, code_store, symbol_state):
        return ValueInfo(ctypes.integer, ValueInfo.LITERAL, self.number.content)

class BinaryOperatorNode(Node):
    """ Expression that is a sum/difference/xor/etc of two expressions. 
    
    left_expr (expression) - expression on left side
    operator (Token) - the token representing this operator
    right_expr (expression) - expression on the right side

    """
    symbol = "expression"

    def __init__(self, left_expr, operator, right_expr):
        super().__init__()

        self.assert_symbol(left_expr, "expression")
        self.left_expr = left_expr
        
        assert isinstance(operator, Token)
        self.operator = operator
        
        self.assert_symbol(right_expr, "expression")
        self.right_expr = right_expr

    def add(self, left_value, right_value, code_store):
        if (left_value.value_type == ctypes.integer and
            left_value.storage_type == ValueInfo.LITERAL and
            right_value.value_type == ctypes.integer and
            right_value.storage_type == ValueInfo.LITERAL):
            return ValueInfo(ctypes.integer,
                             ValueInfo.LITERAL,
                             str(int(left_value.storage_info) +
                                 int(right_value.storage_info)))
        else:
            raise NotImplementedError

    def multiply(self, left_value, right_value, code_store):
        if (left_value.value_type == ctypes.integer and
            left_value.storage_type == ValueInfo.LITERAL and
            right_value.value_type == ctypes.integer and
            right_value.storage_type == ValueInfo.LITERAL):
            return ValueInfo(ctypes.integer,
                             ValueInfo.LITERAL,
                             str(int(left_value.storage_info) *
                                 int(right_value.storage_info)))
        else:
            return NotImplementedError
        
    def make_code(self, code_store, symbol_state):
        left_value = self.left_expr.make_code(code_store, symbol_state)
        right_value = self.right_expr.make_code(code_store, symbol_state)
        
        if self.operator == Token(token_kinds.plus):
            return self.add(left_value, right_value, code_store)
        elif self.operator == Token(token_kinds.star):
            return self.multiply(left_value, right_value, code_store)
        else:
            raise NotImplementedError

class DeclarationNode(Node):
    """Represents info about a line of a general variable declaration(s), like

    int a = 3, *b, c[] = {3, 2, 5};

    Currently only supports declaration of a single integer variable, with no
    initializer.

    variable_name (Token(identifier)) - The identifier representing the new
    variable name.
    stack_space (int) - The number of bytes on the stack that this
    declaration line requires. Used to preallocate space on the stack.

    """
    symbol = "declaration"
    
    def __init__(self, variable_name):
        self.assert_kind(variable_name, token_kinds.identifier)
        self.variable_name = variable_name
        
        self.stack_space = 4
    
    def make_code(self, code_store, symbol_state):
        status = symbol_state.add_symbol(self.variable_name.content,
                                         ctypes.integer)
        # TODO: Real error!
        if not status: raise NotImplementedError
