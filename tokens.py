"""Classes for representing tokens.

A TokenKind instance represents one of the kinds of tokens recognized (see
token_kinds.py). A Token instance represents a token as produced by the lexer.

"""


class TokenKind:
    """Class representing the various known kinds of tokens.

    Ex: +, -, ), return, int

    There are also token kind instances for each of 'identifier' and
    'number'. See token_kinds.py for a list of token_kinds defined.

    text_repr (str) - The token's representation in text, if it has a fixed
    representation.

    """

    def __init__(self, text_repr="", kinds=[]):
        """Initialize a new TokenKind and add it to `kinds`.

        kinds (List[TokenKind]) - List of kinds to which this TokenKind is
        added. This is convenient when defining token kinds in token_kind.py.

        """
        self.text_repr = text_repr
        kinds.append(self)
        kinds.sort(key=lambda kind: -len(kind.text_repr))

    def __str__(self):
        """Return the representation of this token kind."""
        return self.text_repr


class Token:
    """Single unit element of the input as produced by the tokenizer.

    kind (TokenKind) - Kind of this token.

    content - Additional content about some tokens. For number tokens,
    this stores the number itself. For identifiers, this stores the identifier
    name. For string, stores a list of its characters.
    rep (str) - The string representation of this token. If not provided, the
    content parameter is used.
    r (Range) - Range of positions that this token covers.

    """

    def __init__(self, kind, content="", rep="", r=None):
        """Initialize this token."""
        self.kind = kind

        self.content = content if content else str(self.kind)
        self.rep = rep
        self.r = r

    def __repr__(self):  # pragma: no cover
        return self.content

    def __str__(self):
        """Return the token content."""
        return self.rep if self.rep else self.content
