"""Parser logic that parses statement nodes."""

import shivyc.token_kinds as token_kinds
import shivyc.tree.nodes as nodes

from shivyc.parser.declaration import parse_declaration
from shivyc.parser.expression import parse_expression
from shivyc.parser.utils import (add_range, log_error, match_token, token_is,
                                 ParserError)


@add_range
def parse_statement(index):
    """Parse a statement.

    Try each possible type of statement, catching/logging exceptions upon
    parse failures. On the last try, raise the exception on to the caller.

    """
    try:
        return parse_compound_statement(index)
    except ParserError as e:
        log_error(e)

    try:
        return parse_return(index)
    except ParserError as e:
        log_error(e)

    try:
        return parse_if_statement(index)
    except ParserError as e:
        log_error(e)

    try:
        return parse_while_statement(index)
    except ParserError as e:
        log_error(e)

    try:
        return parse_for_statement(index)
    except ParserError as e:
        log_error(e)

    return parse_expr_statement(index)


@add_range
def parse_compound_statement(index):
    """Parse a compound statement.

    A compound statement is a collection of several
    statements/declarations, enclosed in braces.

    """
    index = match_token(index, token_kinds.open_brack, ParserError.GOT)

    # Read block items (statements/declarations) until there are no more.
    items = []
    while True:
        try:
            item, index = parse_statement(index)
            items.append(item)
            continue
        except ParserError as e:
            log_error(e)

        try:
            item, index = parse_declaration(index)
            items.append(item)
            continue
        except ParserError as e:
            log_error(e)
            # When both of our parsing attempts fail, break out of the loop
            break

    index = match_token(index, token_kinds.close_brack, ParserError.GOT)

    return nodes.Compound(items), index


@add_range
def parse_return(index):
    """Parse a return statement.

    Ex: return 5;

    """
    index = match_token(index, token_kinds.return_kw, ParserError.GOT)
    node, index = parse_expression(index)

    index = match_token(index, token_kinds.semicolon, ParserError.AFTER)
    return nodes.Return(node), index


@add_range
def parse_if_statement(index):
    """Parse an if statement."""

    index = match_token(index, token_kinds.if_kw, ParserError.GOT)
    index = match_token(index, token_kinds.open_paren, ParserError.AFTER)
    conditional, index = parse_expression(index)
    index = match_token(index, token_kinds.close_paren, ParserError.AFTER)
    statement, index = parse_statement(index)

    # If there is an else that follows, parse that too.
    is_else = token_is(index, token_kinds.else_kw)
    if not is_else:
        else_statement = None
    else:
        index = match_token(index, token_kinds.else_kw, ParserError.GOT)
        else_statement, index = parse_statement(index)

    return nodes.IfStatement(conditional, statement, else_statement), index


@add_range
def parse_while_statement(index):
    """Parse a while statement."""
    index = match_token(index, token_kinds.while_kw, ParserError.GOT)
    index = match_token(index, token_kinds.open_paren, ParserError.AFTER)
    conditional, index = parse_expression(index)
    index = match_token(index, token_kinds.close_paren, ParserError.AFTER)
    statement, index = parse_statement(index)

    return nodes.WhileStatement(conditional, statement), index


@add_range
def parse_for_statement(index):
    """Parse a for statement."""
    index = match_token(index, token_kinds.for_kw, ParserError.GOT)
    index = match_token(index, token_kinds.open_paren, ParserError.AFTER)

    first, second, third, index = _get_for_clauses(index)
    stat, index = parse_statement(index)

    return nodes.ForStatement(first, second, third, stat), index


def _get_for_clauses(index):
    """Get the three clauses of a for-statement.

    index - Index of the beginning of the first clause.

    returns - Tuple (Node, Node, Node, index). Each Node is the corresponding
    clause, or None if that clause is empty The index is that of first token
    after the close paren terminating the for clauses.

    Raises exception on malformed input.
    """

    first, index = _get_first_for_clause(index)

    if token_is(index, token_kinds.semicolon):
        second = None
        index += 1
    else:
        second, index = parse_expression(index)
        index = match_token(index, token_kinds.semicolon, ParserError.AFTER)

    if token_is(index, token_kinds.close_paren):
        third = None
        index = index + 1
    else:
        third, index = parse_expression(index)
        index = match_token(index, token_kinds.close_paren, ParserError.AFTER)

    return first, second, third, index


def _get_first_for_clause(index):
    """Get the first clause of a for-statement.

    index - Index of the beginning of the first clause in the for-statement.
    returns - Tuple. First element is a node if a clause is found and None if
    there is no clause (i.e. semicolon terminating the clause). Second element
    is an integer index where the next token begins.

    If malformed, raises exception.

    """
    if token_is(index, token_kinds.semicolon):
        return None, index + 1

    try:
        return parse_declaration(index)
    except ParserError as e:
        log_error(e)

    clause, index = parse_expression(index)
    index = match_token(index, token_kinds.semicolon, ParserError.AFTER)
    return clause, index


@add_range
def parse_expr_statement(index):
    """Parse a statement that is an expression.

    Ex: a = 3 + 4

    """
    node, index = parse_expression(index)
    index = match_token(index, token_kinds.semicolon, ParserError.AFTER)
    return nodes.ExprStatement(node), index
