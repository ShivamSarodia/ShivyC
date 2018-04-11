"""Parser logic that parses declaration nodes."""

import shivyc.ctypes as ctypes
from shivyc.errors import error_collector, CompilerError
import shivyc.parser.utils as p
import shivyc.token_kinds as token_kinds
import shivyc.tree.decl_nodes as decl_nodes
import shivyc.tree.nodes as nodes
from shivyc.parser.utils import (add_range, ParserError, match_token, token_is,
                                 raise_error, log_error, token_range, token_in)


@add_range
def parse_func_definition(index):
    """Parse a function definition."""

    specs, index = parse_decl_specifiers(index)
    end = find_decl_end(index)
    decl = parse_declarator(index, end)
    range = token_range(index, end)

    from shivyc.parser.statement import parse_compound_statement
    body, index = parse_compound_statement(end)

    root = decl_nodes.Root(specs, [decl], [None], [range])
    return nodes.Declaration(root, body), index


@add_range
def parse_declaration(index):
    """Parse a declaration into a tree.nodes.Declaration node.

    Example:
        int *a, (*b)[], c

    """
    node, index = parse_decls_inits(index)
    return nodes.Declaration(node), index


def parse_abstract_declarator(start, end):
    """Parse an abstract declarator into a decl_nodes.Node.

    This function raises a ParserError if the parsed entity is a declarator,
    rather than an abstract declarator.
    """
    root = parse_declarator(start, end)
    node = root
    while not isinstance(node, decl_nodes.Identifier):
        node = node.child

    if node.identifier:
        # add error to the error_collector because more of a semantic error
        # than a parsing error
        err = "expected abstract declarator, but identifier name was provided"
        error_collector.add(CompilerError(err, node.identifier.r))

    return root


def parse_spec_qual_list(index):
    """Parse a specifier-qualifier list.

    This function raises a parser error if any other declaration specifiers
    are provided.
    """
    return parse_decl_specifiers(index, True)


def parse_decls_inits(index, parse_inits=True):
    """Parse declarations and initializers into a decl_nodes.Root node.

    The decl_nodes node is used by the caller to create a
    tree.nodes.Declaration node, and the decl_nodes node is traversed during
    the IL generation step to convert it into an appropriate ctype.

    If `parse_inits` is false, do not permit initializers. This is useful
    for parsing struct objects.
    """
    specs, index = parse_decl_specifiers(index)

    # If declaration specifiers are followed directly by semicolon
    if token_is(index, token_kinds.semicolon):
        return decl_nodes.Root(specs, [], [], []), index + 1

    is_typedef = any(tok.kind == token_kinds.typedef_kw for tok in specs)

    decls = []
    ranges = []
    inits = []

    while True:
        end = find_decl_end(index)
        decls.append(parse_declarator(index, end, is_typedef))
        ranges.append(token_range(index, end))

        index = end
        if token_is(index, token_kinds.equals) and parse_inits:
            # Parse initializer expression
            # Currently, only simple initializers are supported
            from shivyc.parser.expression import parse_assignment
            expr, index = parse_assignment(index + 1)
            inits.append(expr)
        else:
            inits.append(None)

        # Expect a comma, break if there isn't one
        if token_is(index, token_kinds.comma):
            index += 1
        else:
            break

    index = match_token(index, token_kinds.semicolon, ParserError.AFTER)

    node = decl_nodes.Root(specs, decls, inits, ranges)
    return node, index


def parse_decl_specifiers(index, spec_qual=False):
    """Parse a declaration specifier.

    Examples:
        int
        const char
        typedef int

    If spec_qual=True, produces a CompilerError if given any specifiers
    that are neither type specifier nor type qualifier.

    The returned `specs` list may contain two types of elements: tokens and
    Node objects. A Node object will be included for a struct or union
    declaration, and a token for all other declaration specifiers.
    """
    type_specs = set(ctypes.simple_types.keys())
    type_specs |= {token_kinds.signed_kw, token_kinds.unsigned_kw}

    type_quals = {token_kinds.const_kw}

    storage_specs = {token_kinds.auto_kw, token_kinds.static_kw,
                     token_kinds.extern_kw, token_kinds.typedef_kw}

    specs = []

    # The type specifier class, either SIMPLE, STRUCT, or TYPEDEF,
    # represents the allowed kinds of type specifiers. Once the first
    # specifier is parsed, the type specifier class is set. If the type
    # specifier class is set to STRUCT or TYPEDEF, no further type
    # specifiers are permitted in the type specifier list. If it is set to
    # SIMPLE, more simple type specifiers are permitted. This is important
    # for typedef parsing.

    SIMPLE = 1
    STRUCT = 2
    TYPEDEF = 3
    type_spec_class = None

    while True:
        # Parse a struct specifier if there is one.
        if not type_spec_class and token_is(index, token_kinds.struct_kw):
            node, index = parse_struct_spec(index + 1)
            specs.append(node)
            type_spec_class = STRUCT

        # Parse a union specifier if there is one.
        elif not type_spec_class and token_is(index, token_kinds.union_kw):
            node, index = parse_union_spec(index + 1)
            specs.append(node)
            type_spec_class = STRUCT

        # Match a typedef name
        elif (not type_spec_class
              and token_is(index, token_kinds.identifier)
              and p.symbols.is_typedef(p.tokens[index])):
            specs.append(p.tokens[index])
            index += 1
            type_spec_class = TYPEDEF

        elif type_spec_class in {None, SIMPLE} and token_in(index, type_specs):
            specs.append(p.tokens[index])
            index += 1
            type_spec_class = SIMPLE

        elif token_in(index, type_quals):
            specs.append(p.tokens[index])
            index += 1

        elif token_in(index, storage_specs):
            if not spec_qual:
                specs.append(p.tokens[index])
            else:
                err = "storage specifier not permitted here"
                error_collector.add(CompilerError(err, p.tokens[index].r))
            index += 1

        else:
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
         token_is(index, token_kinds.identifier) or
         token_is(index, token_kinds.const_kw)):
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


def parse_declarator(start, end, is_typedef=False):
    """Parse the given tokens that comprises a declarator.

    This function parses both declarator and abstract-declarators. For
    an abstract declarator, the Identifier node at the leaf of the
    generated tree has the identifier None.

    Expects the declarator to start at start and end at end-1 inclusive.
    Returns a decl_nodes.Node.
    """
    if start == end:
        return decl_nodes.Identifier(None)

    elif (start + 1 == end and
           p.tokens[start].kind == token_kinds.identifier):
        p.symbols.add_symbol(p.tokens[start], is_typedef)
        return decl_nodes.Identifier(p.tokens[start])

    elif p.tokens[start].kind == token_kinds.star:
        const, index = find_const(start + 1)
        return decl_nodes.Pointer(
            parse_declarator(index, end, is_typedef), const)

    func_decl = try_parse_func_decl(start, end, is_typedef)
    if func_decl: return func_decl

    # First and last elements make a parenthesis pair
    elif (p.tokens[start].kind == token_kinds.open_paren and
           find_pair_forward(start) == end - 1):
        return parse_declarator(start + 1, end - 1, is_typedef)

    # Last element indicates an array type
    elif p.tokens[end - 1].kind == token_kinds.close_sq_brack:
        first = p.tokens[end - 3].kind == token_kinds.open_sq_brack
        number = p.tokens[end - 2].kind == token_kinds.number
        if first and number:
            return decl_nodes.Array(
                int(p.tokens[end - 2].content),
                parse_declarator(start, end - 3, is_typedef))

    raise_error("faulty declaration syntax", start, ParserError.AT)


def try_parse_func_decl(start, end, is_typedef=False):
    """Parse a function declarator between start and end.

    If a function declarator is successfully parsed, returns the
    decl_node.Function object. Otherwise, returns None.
    """
    if not token_is(end - 1, token_kinds.close_paren):
        return None

    open_paren = find_pair_backward(end - 1)
    with log_error():
        params, index = parse_parameter_list(open_paren + 1)
        if index == end - 1:
            return decl_nodes.Function(
                params, parse_declarator(start, open_paren, is_typedef))

    return None


def find_const(index):
    """Check for a continuous sequence of `const`.

    Returns a tuple containing a boolean for whether any such `const`
    sequence exists and the first index that is not a `const`. If no
    `const` is found, returns the index passed in for the second argument.
    """
    has_const = False
    while token_is(index, token_kinds.const_kw):
        index += 1
        has_const = True
    return has_const, index


def parse_parameter_list(index):
    """Parse a function parameter list.

    Returns a list of decl_nodes arguments and the index right after the
    last argument token. This index should be the index of a closing
    parenthesis, but that check is left to the caller.

    index - index right past the opening parenthesis
    """
    # List of decl_nodes arguments
    params = []

    # No arguments
    if token_is(index, token_kinds.close_paren):
        return params, index

    while True:
        # Try parsing declaration specifiers, quit if no more exist
        specs, index = parse_decl_specifiers(index)

        end = find_decl_end(index)
        decl = parse_declarator(index, end)
        range = token_range(index, end)
        params.append(decl_nodes.Root(specs, [decl], None, [range]))

        index = end

        # Expect a comma, and break if there isn't one
        if token_is(index, token_kinds.comma):
            index += 1
        else:
            break

    return params, index


def _parse_struct_union_spec(index, rtype):
    """Parse a struct or union specifier as required rtype.

    index - index right past the type definition keyword.
    rtype - class from decl_nodes that specifies return type.
    """
    start_r = p.tokens[index - 1].r

    name = None
    if token_is(index, token_kinds.identifier):
        name = p.tokens[index]
        index += 1

    members = None
    if token_is(index, token_kinds.open_brack):
        members, index = parse_struct_union_members(index + 1)

    if name is None and members is None:
        err = "expected identifier or member list"
        raise_error(err, index, ParserError.AFTER)

    r = start_r + p.tokens[index - 1].r
    return rtype(name, members, r), index


def parse_struct_spec(index):
    """Parse a struct specifier as a decl_nodes.Struct node.

    index - index right past the `struct` keyword
    """
    return _parse_struct_union_spec(index, decl_nodes.Struct)


def parse_union_spec(index):
    """Parse a union specifier as a decl_nodes.Union node.

    index - index right past the `union` keyword
    """
    return _parse_struct_union_spec(index, decl_nodes.Union)


def parse_struct_union_members(index):
    """Parse the list of members of struct or union as a list of Root nodes.

    index - index right past the open bracket starting the members list
    """
    members = []

    while True:
        if token_is(index, token_kinds.close_brack):
            return members, index + 1

        node, index = parse_decls_inits(index, False)
        members.append(node)
