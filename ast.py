"""Classes for the nodes that form our abstract syntax tree (AST). Each node
corresponds to a rule in the C grammar.

"""

import token_kinds

class Node:
    """A general class for representing a single node in the AST. Inherit all
    AST nodes from this class.

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
            raise ValueError("malformed tree: expected symbol ", symbol_name,
                             ", got ", node.symbol)

    def assert_kind(self, token, kind):
        if token.kind != kind:
            raise ValueError("malformed tree: expected token kind ", kind,
                             ", got ", token.kind)

class MainNode(Node):
    """ General rule for the main function. Will be removed once function
    definition is supported. Ex: int main() { return `return_value`; }
    
    statement (statement) - a statement in main function

    """
    symbol = "main_function"
    
    def __init__(self, statement):
        super().__init__()

        self.assert_symbol(statement, "statement")
        self.statement = statement
        
    def make_code(self, code_store):
        code_store.add_label("main")
        code_store.add_command(("push", "rbp"))
        code_store.add_command(("mov", "rbp", "rsp"))
        self.statement.make_code(code_store)

class ReturnNode(Node):
    """ Return statement

    return_value (expression) - value to return

    """
    symbol = "statement"

    def __init__(self, return_value):
        super().__init__()

        self.assert_symbol(return_value, "expression")
        self.return_value = return_value

    def make_code(self, code_store):
        # For now, the expression always returns its value in the rax register.
        # This will be changed shortly, so the "mov rax rax" command will be
        # made more useful.
        self.return_value.make_code(code_store)
        code_store.add_command(("mov", "rax", "rax"))
        code_store.add_command(("pop", "rbp"))
        code_store.add_command(("ret",))

class NumberNode(Node):
    """ Expression that is just a single number. 

    number (Token(Number)) - number this expression represents

    """
    symbol = "expression"
    
    def __init__(self, number):
        super().__init__()

        assert number.kind == token_kinds.number
        self.number = number

    def make_code(self, code_store):
        code_store.add_command(("mov", "rax", self.number.content))
