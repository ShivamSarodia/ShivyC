"""Entry point for the parser logic that converts a token list to an AST.

Each parse_* function corresponds to a unique non-terminal symbol in the C
grammar. It parses utils.tokens beginning at the given index to try to match
a grammar rule that generates the desired symbol. If a match is found,
it returns a tuple (Node, index) where Node is an AST node for that match
and index is one more than that of the last token consumed in that parse. If no
match is not found, raises an appropriate ParserError.

Whenever a call to a parse_* function raises a ParserError, the calling
function must either catch the exception and log it (using log_error),
or pass the exception on to the caller. A function takes the first approach
if there are other possible parse paths to consider, and the second approach if
the function cannot parse the entity from the tokens.

"""
import shivyc.parser.utils as p
import shivyc.token_kinds as token_kinds
import shivyc.tree.nodes as nodes

from shivyc.errors import error_collector
from shivyc.parser.utils import (add_range, log_error, match_token,
                                 ParserError, raise_error)
from shivyc.parser.statement import parse_compound_statement
from shivyc.parser.declaration import parse_declaration


def parse(tokens_to_parse):
    """Parse the given tokens into an AST.

    Also, as the entry point for the parser, responsible for setting the
    tokens global variable.
    """
    p.best_error = None
    p.tokens = tokens_to_parse

    try:
        return parse_root(0)[0]
    except ParserError as e:
        log_error(e)
        error_collector.add(p.best_error)
        return None


@add_range
def parse_root(index):
    """Parse the given tokens into an AST."""
    items = []
    while True:
        try:
            item, index = parse_main(index)
            items.append(item)
        except ParserError as e:
            log_error(e)
        else:
            continue

        try:
            item, index = parse_declaration(index)
            items.append(item)
        except ParserError as e:
            log_error(e)
        else:
            continue

        # If neither parse attempt above worked, break
        break

    # If there are tokens that remain unparsed, complain
    if not p.tokens[index:]:
        return nodes.Root(items), index
    else:
        raise_error("unexpected token", index, ParserError.AT)


@add_range
def parse_main(index):
    """Parse a main function containing block items.

    Ex: int main() { return 4; }

    """
    err = "expected main function starting"
    index = match_token(index, token_kinds.int_kw, ParserError.AT, err)
    index = match_token(index, token_kinds.main, ParserError.AT, err)
    index = match_token(index, token_kinds.open_paren, ParserError.AT, err)
    index = match_token(index, token_kinds.close_paren, ParserError.AT, err)

    node, index = parse_compound_statement(index)
    return nodes.Main(node), index
