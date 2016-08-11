"""Classes for the nodes that form our abstract syntax tree (AST). Each node
corresponds to a rule in the C grammar and has a make_code funtion that
generates code in our three-address IL.

"""

import errors
import ctypes
import token_kinds

from errors import CompilerError
from il_gen import ILCode
from il_gen import ILValue
from il_gen import LiteralILValue
from il_gen import VariableILValue
from tokens import Token

class Node:
    """A general class for representing a single node in the AST. Inherit all
    AST nodes from this class. Every AST node also has a make_code function that
    accepts a il_code (ILCode) to which the generated IL code should be saved.

    symbol (str) - Each node must set the value of this class attribute to the
    non-terminal symbol the corresponding rule produces. This helps enforce tree
    structure so bugs in the parser do not accidentally slip into output code.

    """
    
    # Enum for symbols produced by a node
    MAIN_FUNCTION = 1
    STATEMENT = 2
    DECLARATION = 3
    EXPRESSION = 4
    
    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def assert_symbol(self, node, symbol_name):
        """Useful for enforcing tree structure. Raises an exception if the
        node represents a rule that does not produce the expected symbol. 

        """
        if node.symbol != symbol_name:
            raise ValueError("malformed tree: expected symbol '" +
                             str(symbol_name) + "' but got '" + str(node.symbol)
                             + "'")

    def assert_symbols(self, node, symbol_names):
        """Useful for enforcing tree structure. Raises an exception if the node
        represents a rule that produces none of the symbols in symbol_names."""
        if node.symbol not in symbol_names:
            raise ValueError("malformed tree: unexpected symbol '"
                             + str(node.symbol) + "'")

    def assert_kind(self, token, kind):
        """Useful for enforcing tree structure. Raises an exception if the token
        does not have the given kind.
        """
        if token.kind != kind:
            raise ValueError("malformed tree: expected token_kind '"
                             + str(kind) + "' but got '" + str(token.kind)
                             + "'")

class MainNode(Node):
    """General rule for the main function. Will be removed once function
    definition is supported.
    
    block_items (List[statement, declaration]) - a list of the statements and
    declarations in the main function
    """
    symbol = Node.MAIN_FUNCTION
    
    def __init__(self, block_items):
        super().__init__()

        for item in block_items:
            self.assert_symbols(item, [self.STATEMENT, self.DECLARATION])
        self.block_items = block_items
        
    def make_code(self, il_code, symbol_table):
        for block_item in self.block_items:
            block_item.make_code(il_code, symbol_table)

        return_node = ReturnNode(NumberNode(Token(token_kinds.number, "0")))
        return_node.make_code(il_code, symbol_table)

class ReturnNode(Node):
    """ Return statement

    return_value (expression) - value to return
    """
    symbol = Node.STATEMENT

    def __init__(self, return_value):
        super().__init__()

        self.assert_symbol(return_value, self.EXPRESSION)
                
        self.return_value = return_value

    def make_code(self, il_code, symbol_table):
        il_value = self.return_value.make_code(il_code, symbol_table)
        if il_value.ctype != ctypes.integer:
            # TODO: raise a type error
            raise NotImplementedError("type error")
        else:
            il_code.add_command(ILCode.RETURN, il_value)

class NumberNode(Node):
    """Expression that is just a single number. 

    number (Token(Number)) - number this expression represents

    """
    symbol = Node.EXPRESSION
    
    def __init__(self, number):
        super().__init__()
        
        self.assert_kind(number, token_kinds.number)
        
        self.number = number

    def make_code(self, il_code, symbol_table):
        return LiteralILValue(ctypes.integer, str(self.number))

class IdentifierNode(Node):
    """Expression that is a single identifier.
    
    identifier (Token(Identifier)) - identifier this expression represents
    """
    symbol = Node.EXPRESSION

    def __init__(self, identifier):
        super().__init__()

        self.assert_kind(identifier, token_kinds.identifier)

        self.identifier = identifier

    def make_code(self, il_code, symbol_table):
        return symbol_table.lookup(self.identifier.content)

class ExprStatementNode(Node):
    """ Contains an expression, because an expression can be a statement. """
    
    symbol = Node.STATEMENT

    def __init__(self, expr):
        super().__init__()
        
        self.assert_symbol(expr, self.EXPRESSION)
        
        self.expr = expr

    def make_code(self, il_code, symbol_table):
        # TODO: consider sending some kind of message to the IL -> ASM stage
        # that the returned ILValue is not going to be used.
        self.expr.make_code(il_code, symbol_table)

class ParenExprNode(Node):
    """ Contains an expression in parentheses """

    symbol = Node.EXPRESSION

    def __init__(self, expr):
        super().__init__()
        
        self.assert_symbol(expr, self.EXPRESSION)
        
        self.expr = expr

    def make_code(self, il_code, symbol_table):
        return self.expr.make_code(il_code, symbol_table)
        
class BinaryOperatorNode(Node):
    """ Expression that is a sum/difference/xor/etc of two expressions. 
    
    left_expr (expression) - expression on left side
    operator (Token) - the token representing this operator
    right_expr (expression) - expression on the right side

    """
    symbol = Node.EXPRESSION

    def __init__(self, left_expr, operator, right_expr):
        super().__init__()

        self.assert_symbol(left_expr, self.EXPRESSION)
        self.assert_symbol(right_expr, self.EXPRESSION)
        
        self.left_expr = left_expr
        self.operator = operator
        self.right_expr = right_expr
            
    def make_code(self, il_code, symbol_table):
        if self.operator == Token(token_kinds.plus):
            # TODO: Consider chosing intelligently which side to make code for
            # first.
            left = self.left_expr.make_code(il_code, symbol_table)
            right = self.right_expr.make_code(il_code, symbol_table)

            if left.ctype != ctypes.integer or right.ctype != ctypes.integer:
                raise NotImplementedError("type error")
            output = ILValue(ctypes.integer)
            il_code.add_command(ILCode.ADD, left, right, output)
            return output
        elif self.operator == Token(token_kinds.star):
            # TODO: Consider chosing intelligently which side to make code for
            # first.
            left = self.left_expr.make_code(il_code, symbol_table)
            right = self.right_expr.make_code(il_code, symbol_table)

            if left.ctype != ctypes.integer or right.ctype != ctypes.integer:
                raise NotImplementedError("type error")
            output = ILValue(ctypes.integer)
            il_code.add_command(ILCode.MULT, left, right, output)
            return output
        elif self.operator == Token(token_kinds.star):
            raise NotImplementedError("multiplication not supported")
        elif self.operator == Token(token_kinds.equals):
            if isinstance(self.left_expr, IdentifierNode):
                right = self.right_expr.make_code(il_code, symbol_table)
                left = symbol_table.lookup(self.left_expr.identifier.content)
                il_code.add_command(ILCode.SET, right, output=left)
            else:
                raise NotImplementedError("expected identifier on left side")
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
    symbol = Node.DECLARATION
    
    def __init__(self, variable_name):
        super().__init__()
        
        self.assert_kind(variable_name, token_kinds.identifier)
        
        self.variable_name = variable_name

    def make_code(self, il_code, symbol_table):
        symbol_table.add(self.variable_name.content, ctypes.integer)
