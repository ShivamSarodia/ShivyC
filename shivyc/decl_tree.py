"""Classes for the nodes that form the declaration and type name tree.

The declaration trees produces by the parser feel "backwards". For example,
the following:

    int *arr[3];

parses to:

    Root([token_kinds.int_kw], Pointer(Array(3, Identifier(tok))))

while the following:

    int (*arr)[3];

parses to:

    Root([token_kinds.int_kw], Array(3, Pointer(Identifier(tok))))

Declaration trees are to be read inside-out. So, the first example above is
an array of 3 pointers to int, and the second example is a pointer to an
array of 3 integers. The DeclarationNode class in tree.py performs the task
of reversing these trees when forming the ctype.

"""


class Node:
    """Base class for all decl_tree nodes."""

    pass


class Root(Node):
    """Represents a list of declaration specifiers.

    specs (List(Tokens)) - list of the declaration specifiers, as tokens
    child (Node) - child declaration node
    r (Range) - range that this declaration node covers
    """

    def __init__(self, specs, child):
        """Generate root node."""
        self.specs = specs
        self.child = child
        self.r = None
        super().__init__()


class Pointer(Node):
    """Represents a pointer to a type."""

    def __init__(self, child):
        """Generate pointer node."""
        self.child = child
        super().__init__()


class Array(Node):
    """Represents an array of a type.

    n (int) - size of the array

    """

    def __init__(self, n, child):
        """Generate array node."""
        self.n = n
        self.child = child
        super().__init__()


class Function(Node):
    """Represents an function with given arguments and returning given type.

    args (List(Node)) - arguments of the functions
    """

    def __init__(self, args, child):
        """Generate array node."""
        self.args = args
        self.child = child
        super().__init__()


class Identifier(Node):
    """Represents an identifier.

    If this is a type name and has no identifier, `identifier` is None.
    """

    def __init__(self, identifier):
        """Generate identifier node from an identifier token."""
        self.identifier = identifier
        super().__init__()
