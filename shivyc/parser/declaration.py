"""Parser logic that parses declaration nodes."""

import shivyc.ctypes as ctypes
import shivyc.decl_tree as decl_tree
import shivyc.parser.utils as p
import shivyc.token_kinds as token_kinds
import shivyc.tree.nodes as nodes
from shivyc.parser.expression import parse_expression
from shivyc.parser.utils import (add_range, ParserError, match_token, token_is,
                                 raise_error)


@add_range
def parse_declaration(index):
    """Parse a declaration.

    Example:
        int *a, (*b)[], c

    """
    specs, index = parse_decl_specifiers(index)

    # If declaration specifiers are followed directly by semicolon
    if token_is(index, token_kinds.semicolon):
        return nodes.Declaration([], []), index + 1

    decls = []
    inits = []
    while True:
        end = find_decl_end(index)
        t = decl_tree.Root(specs, parse_declarator(index, end))
        t.r = p.tokens[index].r + p.tokens[end - 1].r
        decls.append(t)

        index = end
        if token_is(index, token_kinds.equals):
            # Parse initializer expression
            # Currently, only simple initializers are supported
            expr, index = parse_expression(index + 1)
            inits.append(expr)
        else:
            inits.append(None)

        # Expect a comma, break if there isn't one
        if token_is(index, token_kinds.comma):
            index += 1
        else:
            break

    index = match_token(index, token_kinds.semicolon, ParserError.AFTER)
    return nodes.Declaration(decls, inits), index


def parse_decl_specifiers(index):
    """Parse a declaration specifier.

    Examples:
        int
        const char
        typedef int

    """
    decl_specifiers = (list(ctypes.simple_types.keys()) +
                       [token_kinds.signed_kw, token_kinds.unsigned_kw,
                        token_kinds.auto_kw, token_kinds.static_kw,
                        token_kinds.extern_kw])

    specs = []
    while True:
        for spec in decl_specifiers:
            if token_is(index, spec):
                specs.append(p.tokens[index])
                index += 1
                break
        else:
            # If the for loop did not break, quit the while loop
            break

    if specs:
        return specs, index
    else:
        raise_error("expected declaration specifier", index, ParserError.AT)


def find_pair_forward(index,
                      open=token_kinds.open_paren,
                      close=token_kinds.close_paren,
                      mess="mismatched parentheses in declaration"):
    """Find the closing parenthesis for the opening at given index.

    index - position to start search, should be of kind `open`
    open - token kind representing the open parenthesis
    close - token kind representing the close parenthesis
    mess - message for error on mismatch
    """
    depth = 0
    for i in range(index, len(p.tokens)):
        if p.tokens[i].kind == open:
            depth += 1
        elif p.tokens[i].kind == close:
            depth -= 1

        if depth == 0:
            break
    else:
        # if loop did not break, no close paren was found
        raise_error(mess, index, ParserError.AT)
    return i


def find_pair_backward(index,
                       open=token_kinds.open_paren,
                       close=token_kinds.close_paren,
                       mess="mismatched parentheses in declaration"):
    """Find the opening parenthesis for the closing at given index.

    Same parameters as _find_pair_forward above.
    """
    depth = 0
    for i in range(index, -1, -1):
        if p.tokens[i].kind == close:
            depth += 1
        elif p.tokens[i].kind == open:
            depth -= 1

        if depth == 0:
            break
    else:
        # if loop did not break, no open paren was found
        raise_error(mess, index, ParserError.AT)
    return i


def find_decl_end(index):
    """Find the end of the declarator that starts at given index.

    If a valid declarator starts at the given index, this function is
    guaranteed to return the correct end point. Returns an index one
    greater than the last index in this declarator.
    """
    if (token_is(index, token_kinds.star) or
            token_is(index, token_kinds.identifier)):
        return find_decl_end(index + 1)
    elif token_is(index, token_kinds.open_paren):
        close = find_pair_forward(index)
        return find_decl_end(close + 1)
    elif token_is(index, token_kinds.open_sq_brack):
        mess = "mismatched square brackets in declaration"
        close = find_pair_forward(index, token_kinds.open_sq_brack,
                                        token_kinds.close_sq_brack, mess)
        return find_decl_end(close + 1)
    else:
        # Unknown token. If this declaration is correctly formatted,
        # then this must be the end of the declaration.
        return index


def parse_declarator(start, end):
    """Parse the given tokens that comprises a declarator.

    This function parses both declarator and abstract-declarators. For
    an abstract declarator, the Identifier node at the leaf of the
    generated tree has the identifier None.

    Expects the declarator to start at start and end at end-1 inclusive.
    Returns a decl_tree.Node.
    """
    if start == end:
        return decl_tree.Identifier(None)
    elif (start + 1 == end and
           p.tokens[start].kind == token_kinds.identifier):
        return decl_tree.Identifier(p.tokens[start])

    # First and last elements make a parenthesis pair
    elif (p.tokens[start].kind == token_kinds.open_paren and
           find_pair_forward(start) == end - 1):
        return parse_declarator(start + 1, end - 1)

    elif p.tokens[start].kind == token_kinds.star:
        return decl_tree.Pointer(parse_declarator(start + 1, end))

    # Last element indicates a function type
    elif p.tokens[end - 1].kind == token_kinds.close_paren:
        open_paren = find_pair_backward(end - 1)
        params, index = parse_parameter_list(open_paren + 1)
        if index == end - 1:
            return decl_tree.Function(
                params, parse_declarator(start, open_paren))

    # Last element indicates an array type
    elif p.tokens[end - 1].kind == token_kinds.close_sq_brack:
        first = p.tokens[end - 3].kind == token_kinds.open_sq_brack
        number = p.tokens[end - 2].kind == token_kinds.number
        if first and number:
            return decl_tree.Array(int(p.tokens[end - 2].content),
                                   parse_declarator(start, end - 3))

    raise_error("faulty declaration syntax", start, ParserError.AT)


def parse_parameter_list(index):
    """Parse a function parameter list.

    Returns a list of decl_tree arguments and the index right after the
    last argument token. This index should be the index of a closing
    parenthesis, but that check is left to the caller.

    index - index right past the opening parenthesis
    """
    # List of decl_tree arguments
    params = []

    # No arguments
    if token_is(index, token_kinds.close_paren):
        return params, index

    while True:
        # Try parsing declaration specifiers, quit if no more exist
        specs, index = parse_decl_specifiers(index)

        end = find_decl_end(index)
        params.append(
            decl_tree.Root(specs, parse_declarator(index, end)))

        index = end

        # Expect a comma, and break if there isn't one
        if token_is(index, token_kinds.comma):
            index += 1
        else:
            break

    return params, index
