"""Implementation of the ShivyC preprocessor.

Currently, the preprocessor implementation is very simple and only handles
include directives. Despite this, the implementation is also
technically incorrect in many ways. For example, it expands #include
directives wherever they appear, rather than only expanding them when the
appear at the beginning of a line.
"""
import pathlib

import shivyc.lexer as lexer
import shivyc.token_kinds as token_kinds

from shivyc.errors import error_collector, CompilerError


def process(tokens, this_file):
    """Process the given tokens and return the preprocessed token list."""

    processed = []
    i = 0
    while i < len(tokens) - 2:
        if (tokens[i].kind == token_kinds.pound and
            tokens[i + 1].kind == token_kinds.identifier and
            tokens[i + 1].content == "include" and
             tokens[i + 2].kind == token_kinds.include_file):

            # Replace tokens[i] -> tokens[i+2] with preprocessed contents of
            # the included file.
            try:
                file, filename = read_file(tokens[i + 2].content, this_file)
                new_tokens = process(lexer.tokenize(file, filename), filename)
                processed += new_tokens

            except IOError:
                error_collector.add(CompilerError(
                    "unable to read included file",
                    tokens[i + 2].r
                ))

            i += 3

        else:
            processed.append(tokens[i])
            i += 1

    return processed + tokens[i:]


def read_file(include_file, this_file):
    """Read the text of the given include file.

    include_file - the header name, including opening and closing quotes or
    angle brackets.
    this_file - location of the current file being preprocessed. used for
    locating quoted headers.
    """

    if include_file[0] == '"':
        path = pathlib.Path(this_file).parent.joinpath(include_file[1:-1])
    else:  # path is an include file
        path = pathlib.Path(__file__).parent\
            .joinpath("include").joinpath(include_file[1:-1])

    with open(str(path)) as file:
        return file.read(), str(path)
