"""Objects for the parsing phase of the compiler.

This parser is written entirely by hand because automatic parser generators are
no fun.

"""
from collections import namedtuple

import ctypes
import tree
import token_kinds
from errors import ParserError, error_collector
from il_gen import PointerCType, ArrayCType
from tokens import Token


class Parser:
    """Logic for converting a list of tokens into an AST.

    Each internal function parse_* corresponds to a unique non-terminal symbol
    in the C grammar. It parses self.tokens beginning at the given index to try
    to match a grammar rule that generates the desired symbol. If a match is
    found, it returns a tuple (Node, index) where Node is an AST node for that
    match and index is one more than that of the last token consumed in that
    parse. If no match is not found, raises an appropriate ParserError.

    Whenever a call to a parse_* function raises a ParserError, the calling
    function must either catch the exception and log it (using
    self._log_error), or pass the exception on to the caller. A function
    takes the first approach if there are other possible parse paths to
    consider, and the second approach if the function cannot parse the entity
    from the tokens.

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
            self._log_error(e)
            error_collector.add(self.best_error)
            return None

        # Ensure there's no tokens left at after the main function
        if self.tokens[index:]:
            descrip = "unexpected token"
            error_collector.add(
                ParserError(descrip, index, self.tokens, ParserError.AT))

        return node

    def parse_main(self, index):
        """Parse a main function containing block items.

        Ex: int main() { return 4; }

        """
        err = "expected main function starting"
        index = self._match_token(index, token_kinds.int_kw, err,
                                  ParserError.AT)
        index = self._match_token(index, token_kinds.main, err, ParserError.AT)
        index = self._match_token(index, token_kinds.open_paren, err,
                                  ParserError.AT)
        index = self._match_token(index, token_kinds.close_paren, err,
                                  ParserError.AT)

        node, index = self.parse_compound_statement(index)
        return (tree.MainNode(node), index)

    def parse_statement(self, index):
        """Parse a statement.

        Try each possible type of statement, catching/logging exceptions upon
        parse failures. On the last try, raise the exception on to the caller.

        """
        try:
            return self.parse_compound_statement(index)
        except ParserError as e:
            self._log_error(e)

        try:
            return self.parse_return(index)
        except ParserError as e:
            self._log_error(e)

        try:
            return self.parse_if_statement(index)
        except ParserError as e:
            self._log_error(e)

        try:
            return self.parse_while_statement(index)
        except ParserError as e:
            self._log_error(e)

        return self.parse_expr_statement(index)

    def parse_compound_statement(self, index):
        """Parse a compound statement.

        A compound statement is a collection of several
        statements/declarations, enclosed in braces.

        """
        index = self._match_token(index, token_kinds.open_brack,
                                  "expected '{'", ParserError.GOT)

        # Read block items (statements/declarations) until there are no more.
        nodes = []
        while True:
            try:
                node, index = self.parse_statement(index)
                nodes.append(node)
                continue
            except ParserError as e:
                self._log_error(e)

            try:
                node, index = self.parse_declaration(index)
                nodes.append(node)
                continue
            except ParserError as e:
                self._log_error(e)
                # When both of our parsing attempts fail, break out of the loop
                break

        index = self._match_token(index, token_kinds.close_brack,
                                  "expected '}'", ParserError.GOT)

        return (tree.CompoundNode(nodes), index)

    def parse_return(self, index):
        """Parse a return statement.

        Ex: return 5;

        """
        index = self._match_token(index, token_kinds.return_kw,
                                  "expected keyword 'return'", ParserError.GOT)
        return_kw = self.tokens[index - 1]
        node, index = self.parse_expression(index)
        index = self._expect_semicolon(index)
        return (tree.ReturnNode(node, return_kw), index)

    def _parse_if_while(self, index, tok_kind):
        """Parse an if/while statement. For statement_type, see below."""

        nodes = {token_kinds.if_kw: tree.IfStatementNode,
                 token_kinds.while_kw: tree.WhileStatementNode}

        descrip = "expected keyword '{}'".format(tok_kind.text_repr),
        index = self._match_token(index, tok_kind, descrip, ParserError.GOT)
        index = self._match_token(index, token_kinds.open_paren,
                                  "expected '('", ParserError.AFTER)
        conditional, index = self.parse_expression(index)
        index = self._match_token(index, token_kinds.close_paren,
                                  "expected ')'", ParserError.AFTER)
        statement, index = self.parse_statement(index)

        return (nodes[tok_kind](conditional, statement), index)

    def parse_if_statement(self, index):
        """Parse an if statement."""
        return self._parse_if_while(index, token_kinds.if_kw)

    def parse_while_statement(self, index):
        """Parse a while statement."""
        return self._parse_if_while(index, token_kinds.while_kw)

    def parse_expr_statement(self, index):
        """Parse a statement that is an expression.

        Ex: a = 3 + 4

        """
        node, index = self.parse_expression(index)
        index = self._expect_semicolon(index)
        return (tree.ExprStatementNode(node), index)

    def parse_expression(self, index):
        """Parse an expression.

        The index returned is of the first token that could not be parsed
        into the expression. If none could be parsed, an exception is raised as
        usual.

        """
        return ExpressionParser(self.tokens).parse(index)

    type_tokens = {token_kinds.void_kw: ctypes.void,
                   token_kinds.bool_kw: ctypes.bool_t,
                   token_kinds.char_kw: ctypes.char,
                   token_kinds.short_kw: ctypes.short,
                   token_kinds.int_kw: ctypes.integer,
                   token_kinds.long_kw: ctypes.longint}

    def parse_declaration(self, index):
        """Parse a declaration.

        Ex: int a, b = 5, *c;

        Currently, only simple declarations of a single arithmetic type without
        an intializer are supported. Signed and unsigned declarations also
        supported.

        """
        # Parse a signed/unsigned declaration or lack thereof
        signed = True
        if self._next_token_is(index, token_kinds.signed_kw):
            signed = True
            index += 1
        elif self._next_token_is(index, token_kinds.unsigned_kw):
            signed = False
            index += 1

        # Parse the type name
        index = self._expect_type_name(index)
        ctype = self.type_tokens[self.tokens[index - 1].kind]
        if not signed:
            ctype = ctypes.to_unsigned(ctype)

        # Parse any number of stars to indicate pointer type
        while self._next_token_is(index, token_kinds.star):
            ctype = PointerCType(ctype)
            index += 1

        # Parse the identifier name
        index = self._match_token(index, token_kinds.identifier,
                                  "expected identifier", ParserError.AFTER)
        variable_name = self.tokens[index - 1]

        # Parse an array declaration
        if (self._next_token_is(index, token_kinds.open_sq_brack) and
            self._next_token_is(index + 1, token_kinds.number) and
             self._next_token_is(index + 2, token_kinds.close_sq_brack)):
            ctype = ArrayCType(ctype, int(self.tokens[index + 1].content))
            index += 3

        index = self._expect_semicolon(index)

        return tree.DeclarationNode(variable_name, ctype), index

    def _expect_type_name(self, index):
        """Expect a type name at self.tokens[index].

        If one is found, return index+1. Otherwise, raise an appropriate
        ParserError.

        """
        err = "expected type name"

        type_tokens = list(self.type_tokens.keys())
        for tok in type_tokens[:-1]:
            try:
                return self._match_token(index, tok, err, ParserError.GOT)
            except ParserError as e:
                self._log_error(e)

        return self._match_token(index, type_tokens[-1], err, ParserError.GOT)

    def _expect_semicolon(self, index):
        """Expect a semicolon at self.tokens[index].

        If one is found, return index+1. Otherwise, raise an appropriate
        ParserError.

        """
        return self._match_token(index, token_kinds.semicolon,
                                 "expected semicolon", ParserError.AFTER)

    def _next_token_is(self, index, kind):
        """Return true iff the next token is of the given kind."""
        return len(self.tokens) > index and self.tokens[index].kind == kind

    def _match_token(self, index, kind, message, message_type):
        """Raise ParserError if tokens[index] is not of the expected kind.

        If tokens[index] is of the expected kind, returns index + 1.
        Otherwise, raises a ParserError with the given message and
        message_type.

        """
        if (len(self.tokens) > index and self.tokens[index].kind == kind):
            return index + 1
        else:
            raise ParserError(message, index, self.tokens, message_type)

    def _log_error(self, error):
        """Log the error in the parser to be used for error reporting.

        The value of error.amount_parsed is used to determine the amount
        successfully parsed before encountering the error.

        error (ParserError) - Error encountered.

        """
        if (not self.best_error or
                error.amount_parsed >= self.best_error.amount_parsed):
            self.best_error = error


class ExpressionParser:
    """Class for parsing expressions.

    The Parser class above dispatches to this ExpressionParser class for
    parsing expressions. The ExpressionParser implements a shift-reduce parser.

    """

    # Dictionay of key-value pairs {TokenKind: precedence} where higher
    # precedence is higher.
    binary_operators = {token_kinds.plus: 11,
                        token_kinds.star: 12,
                        token_kinds.slash: 12,
                        token_kinds.twoequals: 8,
                        token_kinds.notequal: 8,
                        token_kinds.equals: 1}

    # Dictionary of unary prefix operators {TokenKind: tree.Node}
    unary_prefix_operators = {token_kinds.amp: tree.AddrOfNode,
                              token_kinds.star: tree.DerefNode}

    # The set of tokens that indicate that a postfix operator follows. For
    # example, the open parenthesis indicates a function call follows,
    # and an open square bracket indicates an array subscript follows. These
    # have highest priority.
    posfix_operator_begin = {token_kinds.open_paren,
                             token_kinds.open_sq_brack}

    # The set of assignment_tokens (because these are right-associative)
    assignment_operators = {token_kinds.equals}

    # The set of all token kinds that can be in an expression but are not in
    # binary_operators or unary_prefix_operators. Used to determine when
    # parsing can stop.
    valid_tokens = {token_kinds.number, token_kinds.identifier,
                    token_kinds.open_paren, token_kinds.close_paren,
                    token_kinds.open_sq_brack, token_kinds.close_sq_brack,
                    token_kinds.comma}

    # An item in the parsing stack. The item is either a Node or Token,
    # where the node must generate an expression, and the length is the
    # number of tokens consumed in generating this node.
    StackItem = namedtuple("StackItem", ['item', 'length'])

    def __init__(self, tokens):
        """Initialize parser."""
        self.tokens = tokens
        self.s = []

    def parse(self, index):
        """Parse an expression from the given tokens.

        We parse expressions using a shift-reduce parser. We try to comprehend
        as much as possible of self.tokens past the index as being an
        expression, and the index returned is the first token that could not be
        parsed into the expression. If literally none of it could be parsed as
        an expression, raises an exception like usual.
        """
        # TODO: clean up  the if-statements here
        i = index
        while True:
            # Try all of the possible matches
            if not (self.try_match_number() or
                    self.try_match_identifier() or
                    self.try_match_bin_op(self.tokens[i:]) or
                    self.try_match_unary_prefix(self.tokens[i:]) or
                    self.try_match_function_call() or
                    self.try_match_array_subsc() or
                    self.try_match_paren_expr()):

                # None of the known patterns match!

                # Printing stack here is helpful for debugging.
                # print(stack)

                # If we're at the end of the token list, or we've reached a
                # token that can never appear in an expression, stop reading.
                if i == len(self.tokens):
                    break
                elif (self.tokens[i].kind not in self.valid_tokens and
                      self.tokens[i].kind not in self.binary_operators and
                      self.tokens[i].kind not in self.unary_prefix_operators):
                    break

                # Shift one more token onto the stack
                self.s.append(self.StackItem(self.tokens[i], 1))
                i += 1

        if self.s and isinstance(self.s[0].item, tree.Node):
            return (self.s[0].item, index + self.s[0].length)
        else:
            err = "expected expression"
            raise ParserError(err, index, self.tokens, ParserError.GOT)

    def try_match_number(self):
        """Try matching the top of the stack to a number node.

        Return True on successful match, False otherwise.
        """
        if self.match_kind(-1, token_kinds.number):
            self.reduce(tree.NumberNode(self.s[-1].item), 1)
            return True
        return False

    def try_match_identifier(self):
        """Try matching the top of the stack to an identifier node.

        Return True on successful match, False otherwise.
        """
        if self.match_kind(-1, token_kinds.identifier):
            self.reduce(tree.IdentifierNode(self.s[-1].item), 1)
            return True
        return False

    def try_match_bin_op(self, buffer):
        """Try matching the top of the stack to a binary operator node.

        If the next token indicates a higher-precedence operator, do not
        match the bin op in this function.

        """
        # Ensure last three nodes match to permit precedence calculations.
        if not (self.match_node(-1) and
                self.match_kind_in(-2, self.binary_operators) and
                self.match_node(-3)):
            return False

        if not buffer:
            higher_prec_bin = False
            higher_prec_post = False
            another_assignment = False
        else:
            next = buffer[0]

            # is next token a higher precedence binary operator?
            higher_prec_bin = (next.kind in self.binary_operators and
                               (self.binary_operators[next.kind] >
                                self.binary_operators[self.s[-2].item.kind]))

            # is next token a high-precedence postfix operator?
            higher_prec_post = next.kind in self.posfix_operator_begin

            # is both this token and next token an assignment operator,
            # because assignment operators are right associative?
            another_assignment = ((self.s[-2].item.kind in
                                   self.assignment_operators) and
                                  (next.kind in self.assignment_operators))

        if not (higher_prec_bin or
                higher_prec_post or
                another_assignment):

            node = tree.BinaryOperatorNode(self.s[-3].item,
                                           self.s[-2].item,
                                           self.s[-1].item)
            self.reduce(node, 3)
            return True

        return False

    def try_match_unary_prefix(self, buffer):
        """Try matching the top of the stack to prefix unary operator node."""

        if not (self.match_node(-1) and
                self.match_kind_in(-2, self.unary_prefix_operators)):
            return False

        # Make sure next token is not a postfix operator.
        if not buffer or buffer[0].kind not in self.posfix_operator_begin:
            node = self.unary_prefix_operators[self.s[-2].item.kind]
            self.reduce(node(self.s[-1].item, self.s[-2].item), 2)
            return True

        return False

    def try_match_function_call(self):
        """Try matching the top of the stack to a function call node."""

        i = -1
        args = []

        # Expect top of stack to be `)`
        if not self.match_kind(i, token_kinds.close_paren):
            return False

        i -= 1

        # If next elements match ['EXPR', '('], we have a function with no
        # arguments.
        if (self.match_kind(i, token_kinds.open_paren) and
             self.match_node(i - 1)):
            func = self.s[i - 1].item
            args = [arg.item for arg in args[::-1]]
        else:
            while True:
                try:
                    # Next element must be an expression.
                    if self.match_node(i):
                        args.append(self.s[i])
                    else:
                        return False

                    i -= 1

                    # Next elements can be either a comma or ['EXPR', '(']
                    if self.match_kind(i, token_kinds.comma):
                        i -= 1
                    elif (self.match_kind(i, token_kinds.open_paren) and
                          self.match_node(i - 1)):
                        func = self.s[i - 1].item
                        args = [arg.item for arg in args[::-1]]
                        break
                    else:
                        return False

                except IndexError:
                    return False

        node = tree.FunctionCallNode(func, args)
        self.reduce(node, -i + 1)
        return True

    def try_match_array_subsc(self):
        """Try matching an array subscript postfix operator."""
        if (self.match_kind(-1, token_kinds.close_sq_brack) and
            self.match_node(-2) and
            self.match_kind(-3, token_kinds.open_sq_brack) and
             self.match_node(-4)):

            node = tree.ArraySubscriptNode(self.s[-4].item,
                                           self.s[-2].item,
                                           self.s[-3].item)
            self.reduce(node, 4)
            return True

        return False

    def try_match_paren_expr(self):
        """Try matching a parenthesized expression."""

        if (self.match_kind(-3, token_kinds.open_paren) and
            self.match_node(-2) and
             self.match_kind(-1, token_kinds.close_paren)):

            node = tree.ParenExprNode(self.s[-2].item)
            self.reduce(node, 3)
            return True

        return False

    def match_kind(self, index, kind):
        """Check whether the index-th element in the stack is of given kind."""
        try:
            item = self.s[index].item
            return isinstance(item, Token) and item.kind == kind
        except IndexError:
            return False

    def match_kind_in(self, index, kinds):
        """Check whether index-th element in stack is of one of given kinds."""
        try:
            item = self.s[index].item
            return isinstance(item, Token) and item.kind in kinds
        except IndexError:
            return False

    def match_node(self, index):
        """Check whether the index-th element in the stack is a Node."""
        try:
            return isinstance(self.s[index].item, tree.Node)
        except IndexError:
            return False

    def reduce(self, node, num):
        """Perform a reduce operation on the stack.

        node (Node) - Node to reduce into
        num (int) - Number of elements to reduce and replace with new Node

        """
        length = sum(i.length for i in self.s[-num:])

        del self.s[-num:]
        self.s.append(self.StackItem(node, length))
