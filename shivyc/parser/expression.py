"""Parser logic that parses expression nodes."""

import shivyc.parser.utils as p
import shivyc.token_kinds as token_kinds
import shivyc.tree as tree
import shivyc.tree.decl_nodes as decl_nodes
from shivyc.parser.utils import (add_range, match_token, token_is, ParserError,
                                 raise_error, log_error, token_in)


@add_range
def parse_expression(index):
    """Parse expression."""
    return parse_series(
        index, parse_assignment,
        {token_kinds.comma: tree.MultiExpr})


@add_range
def parse_assignment(index):
    """Parse an assignment expression."""

    # This is a slight departure from the official grammar. The standard
    # specifies that a program is syntactically correct only if the
    # left-hand side of an assignment expression is a unary expression. But,
    # to provide more helpful error messages, we permit the left side to be
    # any non-assignment expression.

    left, index = parse_conditional(index)

    if index < len(p.tokens):
        op = p.tokens[index]
        kind = op.kind
    else:
        op = None
        kind = None

    node_types = {token_kinds.equals: tree.Equals,
                  token_kinds.plusequals: tree.PlusEquals,
                  token_kinds.minusequals: tree.MinusEquals,
                  token_kinds.starequals: tree.StarEquals,
                  token_kinds.divequals: tree.DivEquals,
                  token_kinds.modequals: tree.ModEquals}

    if kind in node_types:
        right, index = parse_assignment(index + 1)
        return node_types[kind](left, right, op), index
    else:
        return left, index


@add_range
def parse_conditional(index):
    """Parse a conditional expression."""
    # TODO: Parse ternary operator
    return parse_logical_or(index)


@add_range
def parse_logical_or(index):
    """Parse logical or expression."""
    return parse_series(
        index, parse_logical_and,
        {token_kinds.bool_or: tree.BoolOr})


@add_range
def parse_logical_and(index):
    """Parse logical and expression."""
    # TODO: Implement bitwise operators here.
    return parse_series(
        index, parse_equality,
        {token_kinds.bool_and: tree.BoolAnd})


@add_range
def parse_equality(index):
    """Parse equality expression."""
    # TODO: Implement relational and shift expressions here.
    return parse_series(
        index, parse_relational,
        {token_kinds.twoequals: tree.Equality,
         token_kinds.notequal: tree.Inequality})


@add_range
def parse_relational(index):
    """Parse relational expression."""
    return parse_series(
        index, parse_bitwise,
        {token_kinds.lt: tree.LessThan,
         token_kinds.gt: tree.GreaterThan,
         token_kinds.ltoe: tree.LessThanOrEq,
         token_kinds.gtoe: tree.GreaterThanOrEq})


@add_range
def parse_bitwise(index):
    return parse_series(
        index, parse_additive,
        {token_kinds.lbitshift: tree.LBitShift,
         token_kinds.rbitshift: tree.RBitShift})


@add_range
def parse_additive(index):
    """Parse additive expression."""
    return parse_series(
        index, parse_multiplicative,
        {token_kinds.plus: tree.Plus,
         token_kinds.minus: tree.Minus})


@add_range
def parse_multiplicative(index):
    """Parse multiplicative expression."""
    return parse_series(
        index, parse_cast,
        {token_kinds.star: tree.Mult,
         token_kinds.slash: tree.Div,
         token_kinds.mod: tree.Mod})


@add_range
def parse_cast(index):
    """Parse cast expression."""

    from shivyc.parser.declaration import (
        parse_abstract_declarator, parse_spec_qual_list)

    with log_error():
        match_token(index, token_kinds.open_paren, ParserError.AT)
        specs, index = parse_spec_qual_list(index + 1)
        node, index = parse_abstract_declarator(index)
        match_token(index, token_kinds.close_paren, ParserError.AT)

        decl_node = decl_nodes.Root(specs, [node])
        expr_node, index = parse_cast(index + 1)
        return tree.Cast(decl_node, expr_node), index

    return parse_unary(index)


@add_range
def parse_unary(index):
    """Parse unary expression."""

    unary_args = {token_kinds.incr: (parse_unary, tree.PreIncr),
                  token_kinds.decr: (parse_unary, tree.PreDecr),
                  token_kinds.amp: (parse_cast, tree.AddrOf),
                  token_kinds.star: (parse_cast, tree.Deref),
                  token_kinds.bool_not: (parse_cast, tree.BoolNot),
                  token_kinds.plus: (parse_cast, tree.UnaryPlus),
                  token_kinds.minus: (parse_cast, tree.UnaryMinus),
                  token_kinds.compl: (parse_cast, tree.Compl)}

    if token_in(index, unary_args):
        parse_func, NodeClass = unary_args[p.tokens[index].kind]
        subnode, index = parse_func(index + 1)
        return NodeClass(subnode), index
    elif token_is(index, token_kinds.sizeof_kw):
        with log_error():
            node, index = parse_unary(index + 1)
            return tree.SizeofExpr(node), index

        from shivyc.parser.declaration import (
            parse_abstract_declarator, parse_spec_qual_list)

        match_token(index + 1, token_kinds.open_paren, ParserError.AFTER)
        specs, index = parse_spec_qual_list(index + 2)
        node, index = parse_abstract_declarator(index)
        match_token(index, token_kinds.close_paren, ParserError.AT)
        decl_node = decl_nodes.Root(specs, [node])

        return tree.SizeofType(decl_node), index + 1
    else:
        return parse_postfix(index)


@add_range
def parse_postfix(index):
    """Parse postfix expression."""
    cur, index = parse_primary(index)

    while True:
        old_range = cur.r

        if token_is(index, token_kinds.open_sq_brack):
            index += 1
            arg, index = parse_expression(index)
            cur = tree.ArraySubsc(cur, arg)
            match_token(index, token_kinds.close_sq_brack, ParserError.GOT)
            index += 1

        elif (token_is(index, token_kinds.dot)
              or token_is(index, token_kinds.arrow)):
            index += 1
            match_token(index, token_kinds.identifier, ParserError.AFTER)
            member = p.tokens[index]

            if token_is(index - 1, token_kinds.dot):
                cur = tree.ObjMember(cur, member)
            else:
                cur = tree.ObjPtrMember(cur, member)

            index += 1

        elif token_is(index, token_kinds.open_paren):
            args = []
            index += 1

            if token_is(index, token_kinds.close_paren):
                return tree.FuncCall(cur, args), index + 1

            while True:
                arg, index = parse_assignment(index)
                args.append(arg)

                if token_is(index, token_kinds.comma):
                    index += 1
                else:
                    break

            index = match_token(
                index, token_kinds.close_paren, ParserError.GOT)

            return tree.FuncCall(cur, args), index

        elif token_is(index, token_kinds.incr):
            index += 1
            cur = tree.PostIncr(cur)
        elif token_is(index, token_kinds.decr):
            index += 1
            cur = tree.PostDecr(cur)
        else:
            return cur, index

        cur.r = old_range + p.tokens[index - 1].r


@add_range
def parse_primary(index):
    """Parse primary expression."""
    if token_is(index, token_kinds.open_paren):
        node, index = parse_expression(index + 1)
        index = match_token(index, token_kinds.close_paren, ParserError.GOT)
        return tree.ParenExpr(node), index
    elif token_is(index, token_kinds.number):
        return tree.Number(p.tokens[index]), index + 1
    elif (token_is(index, token_kinds.identifier)
          and not p.symbols.is_typedef(p.tokens[index])):
        return tree.Identifier(p.tokens[index]), index + 1
    elif token_is(index, token_kinds.string):
        return tree.String(p.tokens[index].content), index + 1
    elif token_is(index, token_kinds.char_string):
        chars = p.tokens[index].content
        return tree.Number(chars[0]), index + 1
    else:
        raise_error("expected expression", index, ParserError.GOT)


def parse_series(index, parse_base, separators):
    """Parse a series of symbols joined together with given separator(s).

    index (int) - Index at which to start searching.
    parse_base (function) - A parse_* function that parses the base symbol.
    separators (Dict(TokenKind -> Node)) - The separators that join
    instances of the base symbol. Each separator corresponds to a Node,
    which is the Node produced to join two expressions connected with that
    separator.
    """
    cur, index = parse_base(index)
    while True:
        for s in separators:
            if token_is(index, s):
                break
        else:
            return cur, index

        tok = p.tokens[index]
        new, index = parse_base(index + 1)
        cur = separators[s](cur, new, tok)
