"""Parser logic that parses expression nodes."""

import parser.utils as p
import token_kinds
import tree

from parser.utils import (add_range, match_token, token_is, ParserError,
                          raise_error)


@add_range
def parse_expression(index):
    """Parse expression."""
    # TODO: Support expressions separated by commas
    return parse_assignment(index)


@add_range
def parse_assignment(index):
    """Parse an assignment expression."""

    # This is a slight departure from the offical grammar. The standard
    # specifies that a program is syntactically correct only if the
    # left-hand side of an assignment expression is a unary expression. But,
    # to provide more helpful error messages, we permit the left side to be
    # any non-assignment expression.

    left, index = parse_conditional(index)
    if token_is(index, token_kinds.equals):
        op = p.tokens[index]
        right, index = parse_assignment(index + 1)
        return tree.BinaryOperatorNode(left, op, right), index
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
        index, tree.BinaryOperatorNode, parse_logical_and,
        [token_kinds.bool_or])


@add_range
def parse_logical_and(index):
    """Parse logical and expression."""
    # TODO: Implement bitwise operators here.
    return parse_series(
        index, tree.BinaryOperatorNode, parse_equality,
        [token_kinds.bool_and])


@add_range
def parse_equality(index):
    """Parse equality expression."""
    # TODO: Implement relational and shift expressions here.
    return parse_series(
        index, tree.BinaryOperatorNode, parse_additive,
        [token_kinds.twoequals, token_kinds.notequal])


@add_range
def parse_additive(index):
    """Parse additive expression."""
    return parse_series(
        index, tree.BinaryOperatorNode, parse_multiplicative,
        [token_kinds.plus, token_kinds.minus])


@add_range
def parse_multiplicative(index):
    """Parse multiplicative expression."""
    return parse_series(
        index, tree.BinaryOperatorNode, parse_unary,
        [token_kinds.star, token_kinds.slash])


@add_range
def parse_cast(index):
    """Parse cast expression."""
    # TODO: Implement cast operation
    return parse_unary(index)


@add_range
def parse_unary(index):
    """Parse unary expression."""
    if index < len(p.tokens):
        tok = p.tokens[index]

    if token_is(index, token_kinds.incr):
        node, index = parse_unary(index + 1)
        return tree.PreIncrNode(node, tok), index
    elif token_is(index, token_kinds.decr):
        node, index = parse_unary(index + 1)
        return tree.PreDecrNode(node, tok), index
    elif token_is(index, token_kinds.amp):
        node, index = parse_cast(index + 1)
        return tree.AddrOfNode(node, tok), index
    elif token_is(index, token_kinds.star):
        node, index = parse_cast(index + 1)
        return tree.DerefNode(node, tok), index
    elif token_is(index, token_kinds.bool_not):
        node, index = parse_cast(index + 1)
        return tree.BoolNotNode(node, tok), index
    else:
        return parse_postfix(index)


@add_range
def parse_postfix(index):
    """Parse postfix expression."""
    cur, index = parse_primary(index)

    while True:
        if len(p.tokens) > index:
            tok = p.tokens[index]

        if token_is(index, token_kinds.open_sq_brack):
            index += 1
            arg, index = parse_expression(index)
            cur = tree.ArraySubscriptNode(cur, arg, tok)
            match_token(index, token_kinds.close_sq_brack, ParserError.GOT)
            index += 1

        elif token_is(index, token_kinds.open_paren):
            args = []
            index += 1

            if token_is(index, token_kinds.close_paren):
                return tree.FunctionCallNode(cur, args, tok), index + 1

            while True:
                arg, index = parse_expression(index)
                args.append(arg)

                if token_is(index, token_kinds.comma):
                    index += 1
                else:
                    break

            index = match_token(
                index, token_kinds.close_paren, ParserError.GOT)

            return tree.FunctionCallNode(cur, args, tok), index

        elif token_is(index, token_kinds.incr):
            index += 1
            cur = tree.PostIncrNode(cur, tok)
        elif token_is(index, token_kinds.decr):
            index += 1
            cur = tree.PostDecrNode(cur, tok)
        else:
            return cur, index


@add_range
def parse_primary(index):
    """Parse primary expression."""
    if token_is(index, token_kinds.open_paren):
        node, index = parse_expression(index + 1)
        index = match_token(index, token_kinds.close_paren, ParserError.GOT)
        return tree.ParenExprNode(node), index
    elif token_is(index, token_kinds.number):
        return tree.NumberNode(p.tokens[index]), index + 1
    elif token_is(index, token_kinds.identifier):
        return tree.IdentifierNode(p.tokens[index]), index + 1
    elif token_is(index, token_kinds.string):
        return tree.StringNode(p.tokens[index]), index + 1
    elif token_is(index, token_kinds.char_string):
        chars = p.tokens[index].content
        return tree.NumberNode(chars[0]), index + 1
    else:
        raise_error("expected expression", index, ParserError.GOT)


def parse_series(index, node, parse_base, separators):
    """Parse a series of symbols joined together with given separator.

    index (int) - Index at which to start searching.
    node (tree.Node) - Node to create.
    parse_base (function) - A parse_* function that parses the base symbol.
    separators (List(TokenKind)) - The separators that join instances of
    the base symbol.
    """
    cur, index = parse_base(index)
    while True:
        any_sep = any(token_is(index, s) for s in separators)
        if any_sep:
            tok = p.tokens[index]
            new, index = parse_base(index + 1)
            cur = node(cur, tok, new)
        else:
            return cur, index
