"""Objects for the lexing phase of the compiler.

The lexing phase takes the entire contents of a raw input file and
generates a flat list of tokens present in that input file.

"""
from collections import namedtuple
import re

import token_kinds

from errors import CompilerError, Position
from tokens import Token
from token_kinds import symbol_kinds, keyword_kinds

# Create namedtuple for tagged characters. Tagged.c is the character that is
# tagged, and Tagged.p is the position of the tagged character.
Tagged = namedtuple("Tagged", ['c', 'p'])


def tokenize(code, filename):
    """Convert given code into a flat list of Tokens.

    lines - List of list of Tagged objects, where each embedded list is a
    separate line in the input program.
    return - List of Token objects.
    """
    tokens = []

    # Store tokens as they are generated
    tokens = []

    lines = split_to_tagged_lines(code, filename)
    join_extended_lines(lines)

    in_comment = False
    for line in lines:
        line_tokens, in_comment = tokenize_line(line, in_comment)
        tokens += line_tokens

    return tokens


def split_to_tagged_lines(text, filename):
    """Split the input text into tagged lines.

    No newline escaping or other preprocessing is done by this function.

    text (str) - Input file contents as a string.
    filename (str) - Input file name.
    return - Tagged lines. List of list of Tagged objects, where each second
    order list is a separate line in the input progam. No newline characters.
    """
    lines = text.splitlines()
    tagged_lines = []
    for line_num, line in enumerate(lines):
        tagged_line = []
        for col, char in enumerate(line):
            p = Position(filename, line_num + 1, col + 1, line)
            tagged_line.append(Tagged(char, p))
        tagged_lines.append(tagged_line)

        line_num += 1

    return tagged_lines


def join_extended_lines(lines):
    """Join together any lines which end in an escaped newline.

    This function modifies the given lines object in place.

    lines - List of list of Tagged objects, where each embedded list is a
    separate line in the input program.
    """
    # TODO: GCC supports \ followed by whitespace. Should ShivyC do this too?

    i = 0
    while i < len(lines):
        if lines[i] and lines[i][-1].c == "\\":
            # There is a next line to collapse into this one
            if i + 1 < len(lines):
                del lines[i][-1]  # remove trailing backslash
                lines[i] += lines[i + 1]  # concatenate with next line
                del lines[i + 1]  # remove next line

                # Decrement i, so this line is checked for a new trailing
                # backslash.
                i -= 1

            # There is no next line to collapse into this one
            else:
                # TODO: print warning?
                del lines[i][-1]  # remove trailing backslash

        i += 1


def tokenize_line(line, in_comment):
    """Tokenize the given single line.

    line - List of Tagged objects.
    in_comment - Whether the first character in this line is part of a
    C-style comment body.
    return - List of Token objects, and boolean indicating whether the next
    character is part of a comment body.
    """
    tokens = []

    # line[chunk_start:chunk_end] is the section of the line currently
    # being considered for conversion into a token; this string will be
    # called the 'chunk'. Everything before the chunk has already been
    # tokenized, and everything after has not yet been examined
    chunk_start = 0
    chunk_end = 0

    while chunk_end < len(line):
        # TODO: Lex include directives properly

        # Check if line[chunk_end:] starts with a symbol token kind
        symbol_kind = match_symbol_kind_at(line, chunk_end)
        next = match_symbol_kind_at(line, chunk_end + 1)

        if in_comment:
            # Next characters end the comment
            if symbol_kind == token_kinds.star and next == token_kinds.slash:
                in_comment = False
                chunk_start = chunk_end + 2
                chunk_end = chunk_start

            # Skip one character
            else:
                chunk_start = chunk_end + 1
                chunk_end = chunk_start

        # If next characters start a comment, skip over them and set
        # in_comment to true
        elif symbol_kind == token_kinds.slash and next == token_kinds.star:
            in_comment = True
            chunk_start = chunk_end + 2
            chunk_end = chunk_start

        # If next character is double quotes, we read the whole string as a
        # token
        elif symbol_kind == token_kinds.dquote:
            chars, end = read_string(line, chunk_end + 1)
            rep = chunk_to_str(line[chunk_end:end + 1])
            tokens.append(Token(token_kinds.string, chars, rep,
                                p=line[chunk_end].p))

            chunk_start = end + 1
            chunk_end = chunk_start

        # If next two characters are //, we skip the rest of this line as
        # a comment.
        elif symbol_kind == token_kinds.slash and next == token_kinds.slash:
            break

        elif symbol_kind:
            symbol_token = Token(symbol_kind, p=line[chunk_end].p)

            add_chunk(line[chunk_start:chunk_end], tokens)
            tokens.append(symbol_token)

            chunk_start = chunk_end + len(symbol_kind.text_repr)
            chunk_end = chunk_start

        elif line[chunk_end].c.isspace():
            add_chunk(line[chunk_start:chunk_end], tokens)
            chunk_start = chunk_end + 1
            chunk_end = chunk_start

        else:
            chunk_end += 1

    # Flush out anything that is left in the chunk to the output
    add_chunk(line[chunk_start:chunk_end], tokens)

    return tokens, in_comment


def chunk_to_str(chunk):
    """Convert the given chunk to a string.

    chunk - list of Tagged characters.
    return - string representation of the list of Tagged characters
    """
    return "".join(c.c for c in chunk)


def match_symbol_kind_at(content, start):
    """Return the longest matching symbol token kind.

    content - List of Tagged objects in which to search for match.
    start (int) - Index, inclusive, at which to start searching for a match.
    returns (TokenType or None) - Symbol token found, or None if no token
    is found.

    """
    for symbol_kind in symbol_kinds:
        try:
            for i, c in enumerate(symbol_kind.text_repr):
                if content[start + i].c != c:
                    break
            else:
                return symbol_kind
        except IndexError:
            pass

    return None


def read_string(line, start):
    """Return a lexed string list in input characters.

    Also returns the index of the string end quote.

    line[start] should be the first character after the opening quote of the
    string to be lexed. This function continues reading characters until
    an unescaped closing quote is reached. The length returned is the
    number of input characters that were read, not the length of the
    string. The latter is the length of the lexed string list.

    The lexed string is a list of integers, where each integer is the
    ASCII value (between 0 and 128) of the corresponding character in
    the string. The returned lexed string includes a null-terminator.

    line - List of Tagged objects for each character in the line.
    start - Index at which to start reading the string.
    """
    i = start
    chars = []

    escapes = {"'": 39,
               '"': 34,
               "?": 63,
               "\\": 92,
               "a": 7,
               "b": 8,
               "f": 12,
               "n": 10,
               "r": 13,
               "t": 9,
               "v": 11}

    while True:
        if i >= len(line):
            descrip = "missing terminating double quote"
            raise CompilerError(
                descrip, line[start - 1].p.file, line[start - 1].p.line)
        elif line[i].c == '"':
            chars.append(0)
            return chars, i
        elif (i + 1 < len(line) and
                      line[i].c == "\\" and
                      line[i + 1].c in escapes):
            chars.append(escapes[line[i + 1].c])
            i += 2
        else:
            chars.append(ord(line[i].c))
            i += 1


def add_chunk(chunk, tokens):
    """Convert chunk into a token if possible and add to tokens.

    If chunk is non-empty but cannot be made into a token, this function
    records a compiler error. We don't need to check for symbol kind tokens
    here because they are converted before they are shifted into the chunk.

    chunk - Chunk to convert into a token, as list of Tagged characters.
    tokens (List[Token]) - List of the tokens thusfar parsed.

    """
    if chunk:
        keyword_kind = match_keyword_kind(chunk)
        if keyword_kind:
            tokens.append(Token(keyword_kind, p=chunk[0].p))
            return

        number_string = match_number_string(chunk)
        if number_string:
            tokens.append(Token(token_kinds.number, number_string,
                                p=chunk[0].p))
            return

        identifier_name = match_identifier_name(chunk)
        if identifier_name:
            tokens.append(Token(token_kinds.identifier, identifier_name,
                                p=chunk[0].p))
            return

        descrip = "unrecognized token at '{}'".format(chunk_to_str(chunk))
        raise CompilerError(descrip, chunk[0].p.file, chunk[0].p.line)


def match_keyword_kind(token_repr):
    """Find the longest keyword token kind with representation token_repr.

    token_repr - Token representation to match exactly, as list of Tagged
    characters.
    returns (TokenKind, or None) - Keyword token kind that matched.

    """
    token_str = chunk_to_str(token_repr)
    for keyword_kind in keyword_kinds:
        if keyword_kind.text_repr == token_str:
            return keyword_kind
    return None


def match_number_string(token_repr):
    """Return a string that represents the given constant number.

    token_repr - List of Tagged characters.
    returns (str, or None) - String representation of the number.

    """
    token_str = chunk_to_str(token_repr)
    return token_str if token_str.isdigit() else None


def match_identifier_name(token_repr):
    """Return a string that represents the name of an identifier.

    token_repr - List of Tagged characters.
    returns (str, or None) - String name of the identifier.

    """
    token_str = chunk_to_str(token_repr)
    if re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", token_str):
        return token_str
    else:
        return None
