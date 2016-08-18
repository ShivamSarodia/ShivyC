"""Objects for the parsing phase of the compiler.

This parser is written entirely by hand because automatic parser generators are
no fun.

"""
from collections import namedtuple

import tree
import token_kinds
from errors import ParserError
from tokens import Token


class MatchError(Exception):
    """Error indicating a failure to match the token_kinds expected.

    This exception is raised only by match_token and match_tokens and is meant
    to be used only internally by the parser.

    """

    pass


class Parser:
    """Logic for converting a list of tokens into an AST.

    Each internal function parse_* corresponds to a unique non-terminal symbol
    in the C grammar. It parses self.tokens beginning at the given index to try
    to match a grammar rule that generates the desired symbol. If a match is
    found, it returns a tuple (Node, index) where Node is an AST node for that
    match and index is one more than that of the last token consumed in that
    parse. If no match is not found, raises an appropriate ParserError.

    Whenever a call to a parse_* function raises a ParserError, the calling
    function must either catch the exception and log it (using self.log_error),
    or pass the exception on to the caller. A function takes the first approach
    if there are other possible parse paths to consider, and the second
    approach if the function cannot parse the entity from the tokens.

    tokens (List(Token)) - The list of tokens to be parsed.
    best_error (ParserError) - The "best error" encountered thusfar. That is,
    out of all the errors encountered thusfar, this is the one that occurred
    after succesfully parsing the most tokens.

    """

    def __init__(self, tokens):
        """Initialize parser."""
        self.tokens = tokens
        self.best_error = None

    def parse(self):
        """Parse the provided list of tokens into an abstract syntax tree (AST).

        returns (Node) - Root node of the generated AST.

        """
        try:
            node, index = self.parse_main(0)
        except ParserError as e:
            self.log_error(e)
            raise self.best_error

        # Ensure there's no tokens left at after the main function
        if self.tokens[index:]:
            err = "unexpected token"
            raise ParserError(err, index, self.tokens, ParserError.AT)

        return node

    def parse_main(self, index):
        """Parse a main function containing block items.

        Ex: int main() { return 4; }

        """
        kinds_before = [token_kinds.int_kw, token_kinds.main,
                        token_kinds.open_paren, token_kinds.close_paren,
                        token_kinds.open_brack]
        try:
            index = self.match_tokens(index, kinds_before)
        except MatchError:
            err = "expected main function starting"
            raise ParserError(err, index, self.tokens, ParserError.AT)

        nodes = []
        while True:
            try:
                node, index = self.parse_statement(index)
                nodes.append(node)
                continue
            except ParserError as e:
                self.log_error(e)

            try:
                node, index = self.parse_declaration(index)
                nodes.append(node)
                continue
            except ParserError as e:
                self.log_error(e)
                # When all of our parsing attempts fail, break out of the loop
                break

        try:
            index = self.match_token(index, token_kinds.close_brack)
        except MatchError:
            err = "expected closing brace"
            raise ParserError(err, index, self.tokens, ParserError.GOT)

        return (tree.MainNode(nodes), index)

    def parse_statement(self, index):
        """Parse a statement.

        Try each possible type of statement, catching/logging exceptions upon
        parse failures. On the last try, raise the exception on to the caller.

        """
        try:
            return self.parse_return(index)
        except ParserError as e:
            self.log_error(e)

        try:
            return self.parse_if_statement(index)
        except ParserError as e:
            self.log_error(e)

        return self.parse_expr_statement(index)

    def parse_return(self, index):
        """Parse a return statement.

        Ex: return 5;

        """
        try:
            index = self.match_token(index, token_kinds.return_kw)
        except MatchError:
            err = "expected return keyword"
            raise ParserError(err, index, self.tokens, ParserError.GOT)

        node, index = self.parse_expression(index)
        index = self.expect_semicolon(index)
        return (tree.ReturnNode(node), index)

    def parse_if_statement(self, index):
        """Parse an if statement."""
        try:
            index = self.match_token(index, token_kinds.if_kw)
        except MatchError:
            err = "expected keyword 'if'"
            raise ParserError(err, index, self.tokens, ParserError.GOT)

        # TODO: Test for this error
        try:
            index = self.match_token(index, token_kinds.open_paren)
        except MatchError:
            err = "expected '('"
            raise ParserError(err, index, self.tokens, ParserError.AFTER)

        # TODO: Test for failure to parse expression
        conditional, index = self.parse_expression(index)

        # TODO: Test for this error
        try:
            index = self.match_token(index, token_kinds.close_paren)
        except MatchError:
            err = "expected ')'"
            raise ParserError(err, index, self.tokens, ParserError.AFTER)

        statement, index = self.parse_statement(index)

        return (tree.IfStatementNode(conditional, statement), index)

    def parse_expr_statement(self, index):
        """Parse a statement that is an expression.

        Ex: a = 3 + 4

        """
        node, index = self.parse_expression(index)
        index = self.expect_semicolon(index)
        return (tree.ExprStatementNode(node), index)

    def parse_expression(self, index):
        """Parse an expression.

        We parse expressions using a shift-reduce parser. We try to comprehend
        as much as possible of self.tokens past the index as being an
        expression, and the index returned is the first token that could not be
        parsed into the expression. If literally none of it could be parsed as
        an expression, raises an exception like usual.

        """
        # Dictionay of key-value pairs {TokenKind: precedence} where higher
        # precedence is higher.
        binary_operators = {token_kinds.plus: 11,
                            token_kinds.star: 12,
                            token_kinds.equals: 1}

        # The set of assignment_tokens (because these are right-associative)
        assignment_operators = {token_kinds.equals}

        # An item in the parsing stack. The item is either a Node or Token,
        # where the node must generate an expression, and the length is the
        # number of tokens consumed in generating this node.
        StackItem = namedtuple("StackItem", ['item', 'length'])
        stack = []

        # TODO: clean up  the if-statements here
        i = index
        while True:
            # If the top of the stack is a number, reduce it to an expression
            # node
            if (stack and isinstance(stack[-1].item, Token) and
                    stack[-1].item.kind == token_kinds.number):
                stack[-1] = StackItem(tree.NumberNode(stack[-1].item), 1)

            # If the top of the stack is an identifier, reduce it to
            # an identifier node
            elif (stack and isinstance(stack[-1].item, Token) and
                  stack[-1].item.kind == token_kinds.identifier):
                stack[-1] = StackItem(tree.IdentifierNode(stack[-1].item), 1)

            # If the top of the stack matches ( expr ), reduce it to a
            # ParenExpr node
            elif (len(stack) >= 3 and isinstance(stack[-1].item, Token) and
                  stack[-1].item.kind == token_kinds.close_paren and
                  isinstance(stack[-2].item, tree.Node) and
                  isinstance(stack[-3].item, Token) and
                  stack[-3].item.kind == token_kinds.open_paren):
                expr = stack[-2]

                del stack[-3:]
                stack.append(
                    StackItem(tree.ParenExprNode(expr.item), expr.length + 2))

            # If the top of the stack matches a binary operator, reduce it to
            # an expression node.
            elif (len(stack) >= 3 and isinstance(stack[-1].item, tree.Node) and
                  isinstance(stack[-2].item, Token) and
                  stack[-2].item.kind in binary_operators.keys() and
                  isinstance(stack[-3].item, tree.Node)

                  # Make sure next token is not higher precedence
                  and not (i < len(self.tokens) and
                           self.tokens[i].kind in binary_operators.keys() and
                           (binary_operators[self.tokens[i].kind] >
                            binary_operators[stack[-2].item.kind]))

                  # Make sure this and next token are not both assignment
                  # tokens, because assignment tokens are right associative.
                  and not (i < len(self.tokens) and
                           stack[-2].item.kind in assignment_operators and
                           self.tokens[i].kind in assignment_operators)):
                left_expr = stack[-3]
                right_expr = stack[-1]
                operator = stack[-2]

                # Remove these last 3 elements
                del stack[-3:]
                stack.append(
                    StackItem(
                        tree.BinaryOperatorNode(left_expr.item, operator.item,
                                                right_expr.item), left_expr.
                        length + operator.length + right_expr.length))
            else:
                # If we're at the end of the token list, or we've reached a
                # token that can never appear in an expression, stop reading.
                # Note we must update this every time the parser is expanded to
                # accept more identifiers.
                if i == len(self.tokens):
                    break
                elif (self.tokens[i].kind != token_kinds.number and
                      self.tokens[i].kind != token_kinds.identifier and
                      self.tokens[i].kind != token_kinds.open_paren and
                      self.tokens[i].kind != token_kinds.close_paren and
                      self.tokens[i].kind not in binary_operators.keys()):
                    break

                stack.append(StackItem(self.tokens[i], 1))
                i += 1

        if stack and isinstance(stack[0].item, tree.Node):
            return (stack[0].item, index + stack[0].length)
        else:
            err = "expected expression"
            raise ParserError(err, index, self.tokens, ParserError.GOT)

    def parse_declaration(self, index):
        """Parse a declaration.

        Ex: int a, b = 5, *c;

        Currently, only simple declarations of a single integer without an
        intializer are supported.

        """
        try:
            index = self.match_token(index, token_kinds.int_kw)
        except MatchError:
            err = "expected type name"
            raise ParserError(err, index, self.tokens, ParserError.GOT)

        try:
            index = self.match_token(index, token_kinds.identifier)
        except MatchError:
            err = "expected identifier"
            raise ParserError(err, index, self.tokens, ParserError.AFTER)

        variable_name = self.tokens[index - 1]

        index = self.expect_semicolon(index)

        return (tree.DeclarationNode(variable_name), index)

    def expect_semicolon(self, index):
        """Expect a semicolon at self.tokens[index].

        If one is found, return index+1. Otherwise, raise an appropriate
        ParserError.

        """
        try:
            return self.match_token(index, token_kinds.semicolon)
        except MatchError:
            err = "expected semicolon"
            raise ParserError(err, index, self.tokens, ParserError.AFTER)

    #
    # Utility functions for the parser
    #
    def match_token(self, index, kind_expected):
        """Check if self.tokens[index] is of the token kind expected.

        This function is shorthand for match_tokens for a single token.

        """
        return self.match_tokens(index, [kind_expected])

    def match_tokens(self, index, kinds_expected):
        """Check if self.tokens matches the expected token kinds.

        If the tokens all have the expected kinds, starting at the given index,
        this function returns the index one more than the last matched
        element. Otherwise, raises a MatchException.

        index (int) - Index at which to begin matching.
        kinds_expected (List[TokenKind, None]) - List of token kinds expected.

        """
        tokens = self.tokens[index:]
        if len(tokens) < len(kinds_expected):
            raise MatchError()
        elif all(kind == token.kind
                 for kind, token in zip(kinds_expected, tokens)):
            return index + len(kinds_expected)
        else:
            raise MatchError()

    def log_error(self, error):
        """Log the error in the parser to be used for error reporting.

        The value of error.amount_parsed is used to determine the amount
        successfully parsed before encountering the error.

        error (ParserError) - Error encountered.

        """
        if (not self.best_error or
                error.amount_parsed >= self.best_error.amount_parsed):
            self.best_error = error
