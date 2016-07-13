"""Defines a TokenKind class and Token class

A TokenKind instance represents one of the various kinds of tokens recognized. A
Token instance represents a token as produced by the lexer.

"""

class TokenKind:
    """A general class for defining the various known kinds of tokens, such as:
           +, -, ), return, int

    token_id (int) - A unique ID assigned to each token
    text_repr (str) - The way this token looks in text. Used only by the lexer
    to tokenize the input.

    """

    # Stores the ID that should be assigned to the next instance of this
    # class. Incremented each time we create a new instance, so each instance
    # gets a unique ID.
    current_id = 0
    # Stores all the TokenKind instances created. Used by the lexer to iterate
    # through for tokenizing.
    all_kinds = []
            
    def __init__(self, text_repr = ""):
        self.text_repr = text_repr
        
        self.token_id = TokenKind.current_id
        TokenKind.current_id += 1

        TokenKind.all_kinds.append(self)

    def __eq__(self, other):
        return self.token_id == other.token_id
    
class Token:
    """A single unit element of the input. Produced by the tokenizing phase of
    the lexer.
    
    token_kind (TokenKind) - The kind of this token
    content (str) - Stores additional content for some tokens:
        1) For number tokens, stores the number itself
        2) For identifiers, stores the identifier name

    """
    def __init__(self, token_kind, content = ""):
        self.token_kind = token_kind
        self.content = content
