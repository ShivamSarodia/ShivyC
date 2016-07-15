"""Classes for the nodes that form our abstract syntax tree (AST). Each node
corresponds to a rule in the C grammar.

"""

class Node:
    """A general class for representing a single node in the AST. Inherit all
    AST nodes from this class.

    """
    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

class MainNode(Node):
    """ General rule for the main function. Will be removed once function
    definition is supported.

    Ex: int main() { return `return_value`; }

    return_value (Token(Number)) - The number to return

    """
    def __init__(self, return_value):
        super().__init__()
        self.return_value = return_value
