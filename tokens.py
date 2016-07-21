"""Defines a TokenKind class and Token class

A TokenKind instance represents one of the various kinds of tokens recognized. A
Token instance represents a token as produced by the lexer.

"""

class TokenKind:
    """A general class for defining the various known kinds of tokens, such as:
           +, -, ), return, int
    We define a bunch of TokenKind objects in token_kinds.py, and treat these as
    const objects.

    kind_id (int) - A unique ID assigned to each token
    text_repr (str) - The way this token looks in text. Used only by the lexer
    to tokenize the input.

    """

    # Stores the ID that should be assigned to the next instance of this
    # class. Incremented each time we create a new instance, so each instance
    # gets a unique ID.
    current_id = 0
            
    def __init__(self, text_repr = "", kinds = []):
        """Initializes a new TokenKind and adds it to the list of kinds
        passed in.

        text_repr (str) - See class docstring
        kinds (List[TokenKind]) - A list of kinds to which this TokenKind is
        automatically added

        """
        self.text_repr = text_repr
        self.kind_id = self.__class__.current_id

        self.__class__.current_id += 1
        kinds.append(self)

    def __eq__(self, other):
        return self.kind_id == other.kind_id

    def __str__(self):
        return self.text_repr

    def __hash__(self):
        return self.kind_id
    
class Token:
    """A single unit element of the input. Produced by the tokenizing phase of
    the lexer.
    
    kind (TokenKind) - The kind of this token
    content (str) - Stores additional content for some tokens:
        1) For number tokens, stores the number itself
        2) For identifiers, stores the identifier name
    file_name (str) - The name of the file from which this token came. Used for
    error reporting.
    line_num (int) - The line number from which this token came. Used for error
    reporting.

    """
    def __init__(self, kind, content = ""):
        self.kind = kind
        self.content = content if content else str(self.kind)
        self.file_name = None
        self.line_num = None
        
    def __eq__(self, other):
        return self.kind == other.kind and self.content == other.content

    def __str__(self):
        return self.content
