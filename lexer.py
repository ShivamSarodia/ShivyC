"""Defines functions for the lexing phase of the compiler

The lexing phase takes a raw text string as input from the preprocessor and
generates a flat list of tokens present in that text string. Because there's
currently no preproccesor implemented, the input text string is simply the file
contents.

"""

from errors import CompilerError
from tokens import TokenKind
from tokens import Token
import token_kinds

class Lexer:
    """The environment for running tokenize() and associated functions.
    Effectively, creates a closure for tokenize().

    symbol_kinds (List[TokenKind]) - A list of all the concrete token kinds that
    are not keywords. These should split into a new token even when they are not
    surrounded by whitespace, like the plus in `a+b`. Sorted from longest to
    shortest.

    keyword_kinds (List[TokenKind]) - A list of all the concrete tokens that are
    not splitting. These are just the keywords, afaik. Sorted from longest to
    shortest.

    """
    def __init__(self, symbol_kinds, keyword_kinds):
        self.symbol_kinds = sorted(symbol_kinds,
                                   key=lambda kind: -len(kind.text_repr))
        self.keyword_kinds = sorted(keyword_kinds,
                                    key=lambda kind: -len(kind.text_repr))
        
    def tokenize(self, code_lines):
        """Convert the given lines of code into a list of tokens.
        
        The tokenizing algorithm proceeds through the content linearly in one
        pass, producing the list of tokens as we go. Has direct external
        reference to token_kinds.number.

        content (List(tuple)) - The lines of code to tokenize, provided in the
        following form:

           [("int main()", "main.c", 1),
            ("{", "main.c", 2),
            ("return 5;", "main.c", 3),
            ("}", "main.c", 4)]

        where the first element is the contents of the line, the second is the
        file name, and the third is the line number.
        
        returns (List[Token]) - A list of the tokens parsed from the input
        string

        """

        all_tokens = []
        for line_with_info in code_lines:
            # This strange logic allows the tokenize_line function to be
            # ignorant to the file-context of the line passed in.
            try:
                tokens = self.tokenize_line(line_with_info[0])
            except CompilerError as e:
                e.file_name = line_with_info[1]
                e.line_num = line_with_info[2]
                raise e
                
            for token in tokens:
                token.file_name = line_with_info[1]
                token.line_num = line_with_info[2]
                all_tokens.append(token)
        return all_tokens

    def tokenize_line(self, line):
        """Convert the given line of code into a list of tokens that have no
        file-context dependent attributes (like line number) set.

        line (str) - a line of code
        returns (Token) - a token without file-context dependent attributes

        """
        
        # line[chunk_start:chunk_end] is the section of the line currently
        # being considered for conversion into a token; this string will be
        # called the 'chunk'. Everything before the chunk has already been
        # tokenized, and everything after has not yet been examined
        chunk_start = 0
        chunk_end = 0

        # Stores the tokens as they are generated
        tokens = []

        # While we still have characters in the line left to parse
        while chunk_end < len(line):
            # Checks if line[chunk_end:] starts with a symbol token kind
            symbol_kind = self.match_symbol_kind_at(line, chunk_end)
            if symbol_kind:
                symbol_token = Token(symbol_kind)

                self.add_chunk(line[chunk_start:chunk_end], tokens)
                tokens.append(symbol_token)

                chunk_start = chunk_end + len(symbol_kind.text_repr)
                chunk_end = chunk_start
        
            elif line[chunk_end].isspace():
                self.add_chunk(line[chunk_start:chunk_end], tokens)
                chunk_start = chunk_end + 1
                chunk_end = chunk_start

            else:
                chunk_end += 1

        # Flush out anything that is left in the chunk to the output
        self.add_chunk(line[chunk_start:chunk_end], tokens)

        return tokens
            
    def match_symbol_kind_at(self, content, start):
        """Return the longest symbol token kind that matches the content string
        starting at the indicated index, or None if no symbol token matches.
        
        content (str) - The input string to tokenize
        start (int) - The index, inclusive, at which to start searching for a
        token match
        returns (TokenType, None) - The symbol token found, or None if no token
        is found

        """
        for symbol_kind in self.symbol_kinds:
            if content.startswith(symbol_kind.text_repr, start):
                return symbol_kind
        return None

    def add_chunk(self, chunk, tokens):
        """Convert the provided chunk into a token and add to the provided
        tokens variable. If chunk is non-empty but cannot be made into a token,
        raise a compiler error.

        chunk (str) - The chunk to convert into a token
        tokens (List[Token]) - A list of the tokens thusfar parsed

        """
        if chunk:
            keyword_kind = self.match_keyword_kind(chunk)
            if keyword_kind:
                tokens.append(Token(keyword_kind))
                return

            number_string = self.match_number_string(chunk)
            if number_string:
                tokens.append(Token(token_kinds.number,
                                     number_string))
                return

            raise CompilerError("unrecognized token: '{}'".format(chunk))
            
    def match_keyword_kind(self, token_repr):
        """Return the longest keyword token kind with representation exactly
        equal to the given token_repr, or None if not found.

        token_repr (str) - The token representation to match
        returns (TokenKind, or None) - The keyword token kind that matched

        """
        for keyword_kind in self.keyword_kinds:
            if keyword_kind.text_repr == token_repr:
                return keyword_kind
        return None

    def match_number_string(self, token_repr):
        """Return a string that represents the given constant number, or None if
        not possible

        token_repr (str) - The string to make into a token
        returns (str, or None) - The string representation of the number

        """
        return token_repr if token_repr.isdigit() else None
