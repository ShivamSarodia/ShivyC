"""Classes for the nodes that form the declaration and type name tree.

This tree/node system is pretty distinct from the tree/node system used for
the rest of the AST because parsing declarations is very different from
parsing other parts of the language due to the "backwards"-ness of C
declaration syntax, as described below:

The declaration trees produces by the parser feel "backwards". For example,
the following:

    int *arr[3];

parses to:

    Root([token_kinds.int_kw], [Pointer(Array(3, Identifier(tok)))])

while the following:

    int (*arr)[3];

parses to:

    Root([token_kinds.int_kw], [Array(3, Pointer(Identifier(tok)))])

Declaration trees are to be read inside-out. So, the first example above is
an array of 3 pointers to int, and the second example is a pointer to an
array of 3 integers. The DeclarationNode class in tree.py performs the task
of reversing these trees when forming the ctype.

"""

import shivyc.token_kinds as token_kinds


class DeclNode:
    """Base class for all decl_nodes nodes."""

    pass


class Root(DeclNode):
    """Represents a list of declaration specifiers and declarators.

    specs (List(Tokens/Nodes)) - list of the declaration specifiers, as tokens
    decls (List(Node)) - list of declarator nodes
    """

    def __init__(self, specs, decls, inits=None):
        """Generate root node."""
        self.specs = specs
        self.decls = decls

        if inits:
            self.inits = inits
        else:
            self.inits = [None] * len(self.decls)

        super().__init__()


class Pointer(DeclNode):
    """Represents a pointer to a type."""

    def __init__(self, child, const):
        """Generate pointer node.

        const - boolean indicating whether this pointer is const
        """
        self.child = child
        self.const = const
        super().__init__()


class Array(DeclNode):
    """Represents an array of a type.

    n (int) - size of the array

    """

    def __init__(self, n, child):
        """Generate array node."""
        self.n = n
        self.child = child
        super().__init__()


class Function(DeclNode):
    """Represents an function with given arguments and returning given type.

    args (List(Node)) - arguments of the functions
    """

    def __init__(self, args, child):
        """Generate array node."""
        self.args = args
        self.child = child
        super().__init__()


class Identifier(DeclNode):
    """Represents an identifier.

    If this is a type name and has no identifier, `identifier` is None.
    """

    def __init__(self, identifier):
        """Generate identifier node from an identifier token."""
        self.identifier = identifier
        super().__init__()


class _StructUnion(DeclNode):
    """Base class to represent a struct or a union C type.

    tag (Token) - Token containing the tag of this struct
    members (List(Node)) - List of decl_nodes nodes of members, or None
    r (Range) - range that the specifier covers
    """

    def __init__(self, tag, members, r):
        self.tag = tag
        self.members = members

        # These r and kind members are a little hacky. They allow the
        # make_specs_ctype function in tree.nodes.Declaration to treat this
        # as a Token for the purposes of determining the base type of the
        # declaration.
        self.r = r

        super().__init__()


class Struct(_StructUnion):
    """Represents a struct C type."""

    def __init__(self, tag, members, r):
        self.kind = token_kinds.struct_kw
        super().__init__(tag, members, r)


class Union(_StructUnion):
    """Represents a union C type."""

    def __init__(self, tag, members, r):
        self.kind = token_kinds.union_kw
        super().__init__(tag, members, r)
