"""Classes for the nodes that form our abstract syntax tree (AST). Each node
corresponds to a rule in the C grammar.

"""

from code_gen import ValueInfo
from code_gen import ASTData
from errors import CompilerError
import errors
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

    ast_data (ASTData) - Each node must set ast_data appropriately. Generally,
    leaf nodes can construct a new ASTData object and set any required values
    as needed. Non-leaf nodes generally set ast_data as the sum of their
    children ast_data objects.    

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
            raise ValueError("malformed tree: expected symbol '" + symbol_name +
                             "' but got '" + node.symbol + "'")

    def assert_symbols(self, node, symbol_names):
        """Useful for enforcing tree structure. Raises an exception if the node
        represents a rule that produces none of the symbols in symbol_names."""
        if node.symbol not in symbol_names:
            raise ValueError("malformed tree: unexpected symbol '"
                             + node.symbol + "'")

    def assert_kind(self, token, kind):
        """Useful for enforcing tree structure. Raises an exception if the token
        does not have the given kind.
        """
        if token.kind != kind:
            raise ValueError("malformed tree: expected token_kind '"
                             + kind + "' but got '" + token.kind + "'")

class MainNode(Node):
    """ General rule for the main function. Will be removed once function
    definition is supported.
    
    statements (List[statement]) - a list of the statement in main function

    """
    symbol = "main_function"
    
    def __init__(self, block_items):
        super().__init__()

        for item in block_items:
            self.assert_symbols(item, ["statement", "declaration"])
        self.block_items = block_items

        self.ast_data = sum((item.ast_data for item in block_items), ASTData())
        
    def make_code(self, code_store, symbol_state):
        # We pre-allocate some space on the stack by moving the RSP, and restore
        # the RSP before returning from the function. We align the stack shift
        # to be a multiple of 16 so the stack frame is always aligned to a
        # multiple of 16
        symbol_state.stack_shift = self.ast_data.stack_space_required
        if symbol_state.stack_shift % 16 != 0:
            symbol_state.stack_shift += 16 - (symbol_state.stack_shift % 16)

        code_store.add_label("main")
        code_store.add_command(("push", "rbp"))
        code_store.add_command(("mov", "rbp", "rsp"))
                    
        # Reserve the required amount of space on the stack
        if symbol_state.stack_shift:
            code_store.add_command(("sub", "rsp",
                                    str(symbol_state.stack_shift)))
        
        with symbol_state.new_symbol_table():
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

        self.ast_data = return_value.ast_data

    def make_code(self, code_store, symbol_state):
        value_info = self.return_value.make_code(code_store, symbol_state)
        if value_info.has_types(ctypes.integer, ValueInfo.LITERAL):
            code_store.add_command(("mov", "eax", value_info.storage_info))
        elif value_info.has_types(ctypes.integer, ValueInfo.STACK):
            location = "DWORD [rbp - " + str(value_info.storage_info) + "]"
            code_store.add_command(("mov", "eax", location))
        else:
            raise NotImplementedError

        # Move RSP back to where it was before the function executed
        if symbol_state.stack_shift:
            code_store.add_command(("add", "rsp",
                                    str(symbol_state.stack_shift)))
        code_store.add_command(("pop", "rbp"))
        code_store.add_command(("ret",))

class NumberNode(Node):
    """Expression that is just a single number. 

    number (Token(Number)) - number this expression represents

    """
    symbol = "expression"
    
    def __init__(self, number):
        super().__init__()
        
        self.assert_kind(number, token_kinds.number)
        
        self.number = number

        self.ast_data = ASTData()

    def make_code(self, code_store, symbol_state):
        return ValueInfo(ctypes.integer, ValueInfo.LITERAL, self.number.content)

class IdentifierNode(Node):
    """ Expression that is a single identifier.
    
    identifier (Token(Identifier)) - identifier this expression represents
    """
    symbol = "expression"

    def __init__(self, identifier):
        super().__init__()

        self.assert_kind(identifier, token_kinds.identifier)

        self.identifier = identifier

        self.ast_data = ASTData()

    def make_code(self, code_store, symbol_state):
        return symbol_state.get_symbol_or_error(self.identifier)

class ExprStatementNode(Node):
    """ Contains an expression, because an expression can be a statement. """
    
    symbol = "statement"

    def __init__(self, expr):
        super().__init__()
        
        self.assert_symbol(expr, "expression")
        
        self.expr = expr

        self.ast_data = expr.ast_data

    def make_code(self, code_store, symbol_state):
        self.expr.make_code(code_store, symbol_state)
    
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
        self.assert_symbol(right_expr, "expression")
        
        self.left_expr = left_expr
        self.operator = operator
        self.right_expr = right_expr

        self.ast_data = left_expr.ast_data + right_expr.ast_data

    def add(self, left_value, right_value, code_store):
        """Generate code for addition of values

        left_value (ValueInfo) - the ValueInfo returned by make_code on the
        left argument
        right_value (ValueInfo) - the ValueInfo returned by make_code on the
        right argument
        """
        if (left_value.has_types(ctypes.integer, ValueInfo.LITERAL)
            and right_value.has_types(ctypes.integer, ValueInfo.LITERAL)):
            return ValueInfo(ctypes.integer,
                             ValueInfo.LITERAL,
                             str(int(left_value.storage_info) +
                                 int(right_value.storage_info)))
        else:
            raise NotImplementedError

    def multiply(self, left_value, right_value, code_store):
        """Generate code for multiplication of values

        left_value (ValueInfo) - the ValueInfo returned by make_code on the
        left argument
        right_value (ValueInfo) - the ValueInfo returned by make_code on the
        right argument
        """
        if (left_value.has_types(ctypes.integer, ValueInfo.LITERAL)
            and right_value.has_types(ctypes.integer, ValueInfo.LITERAL)):
            return ValueInfo(ctypes.integer,
                             ValueInfo.LITERAL,
                             str(int(left_value.storage_info) *
                                 int(right_value.storage_info)))
        else:
            return NotImplementedError

    def equals(self, left_expr, right_value, code_store, symbol_state):
        """Generate code for setting left_expr equal to right_value

        left_expr (Node(expression)) - Node representing the left side of equals
        sign
        right_value (ValueInfo) - ValueInfo returned by make_code on the right
        argument
        """
        if isinstance(left_expr, IdentifierNode):
            left_value = symbol_state.get_symbol_or_error(left_expr.identifier)

            location = "DWORD [rbp - " + str(left_value.storage_info) + "]"
            if (left_value.has_types(ctypes.integer, ValueInfo.STACK)
                and right_value.has_types(ctypes.integer, ValueInfo.LITERAL)):
                code_store.add_command(("mov", location,
                                        right_value.storage_info))
                return right_value
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError
            
    def make_code(self, code_store, symbol_state):
        left_value = self.left_expr.make_code(code_store, symbol_state)
        right_value = self.right_expr.make_code(code_store, symbol_state)
        
        if self.operator == Token(token_kinds.plus):
            return self.add(left_value, right_value, code_store)
        elif self.operator == Token(token_kinds.star):
            return self.multiply(left_value, right_value, code_store)
        elif self.operator == Token(token_kinds.equals):
            return self.equals(self.left_expr, right_value, code_store,
                               symbol_state)
        else:
            raise errors.token_error("unsupported binary operator: '{}'",
                                     self.operator)
        
class DeclarationNode(Node):
    """Represents info about a line of a general variable declaration(s), like

    int a = 3, *b, c[] = {3, 2, 5};

    Currently only supports declaration of a single integer variable, with no
    initializer.

    variable_name (Token(identifier)) - The identifier representing the new
    variable name.

    """
    symbol = "declaration"
    
    def __init__(self, variable_name):
        super().__init__()
        
        self.assert_kind(variable_name, token_kinds.identifier)
        
        self.variable_name = variable_name

        self.ast_data = ASTData(stack_space_required=4)
            
    def make_code(self, code_store, symbol_state):
        status = symbol_state.add_symbol(self.variable_name.content,
                                         ctypes.integer)
        if not status:
            raise errors.token_error("redeclaration of '{}'",
                                     self.variable_name)
