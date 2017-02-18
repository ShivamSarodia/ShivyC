"""Tests for the parser phase of the compiler."""

import unittest

import tree
import token_kinds
from errors import error_collector
from parser import Parser
from tokens import Token
from tests.test_utils import TestUtils


class ParserTestUtil(TestUtils):
    """Utilities for parser tests."""

    def setUp(self):
        """Clear the error collector before each new test."""
        error_collector.clear()

    def tearDown(self):
        """Assert there are no remaining errors."""
        self.assertNoIssues()

    def assertParsesTo(self, tokens, nodes):
        """Assert the given tokens parse to the given tree nodes.

        This method adds the 'int main() { }' so no need to include those
        tokens in the input list. Similarly, nodes need not include the
        tree.MainNode, just a list of the nodes within.

        """
        ast_root = Parser(self._token_wrap_main(tokens)).parse()
        self.assertEqual(ast_root, tree.MainNode(tree.CompoundNode(nodes)))

    def assertParserError(self, tokens, descrip):
        """Assert the given tokens create a compiler error.

        As above, no need to include 'int main() { }' in the tokens.

        """
        Parser(self._token_wrap_main(tokens)).parse()
        self.assertIssues([descrip])

    def _token_wrap_main(self, tokens):
        """Prefix the `tokens` list with 'int main() {' and suffix with '}'."""
        start_main = [Token(token_kinds.int_kw), Token(token_kinds.main),
                      Token(token_kinds.open_paren),
                      Token(token_kinds.close_paren),
                      Token(token_kinds.open_brack)]
        return start_main + tokens + [Token(token_kinds.close_brack)]


class GeneralTests(ParserTestUtil):
    """General tests of the parser."""

    def test_main_function(self):  # noqa: D400, D403
        """int main() { return 15; }"""
        tokens = [Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15"),
                  Token(token_kinds.semicolon)]

        self.assertParsesTo(tokens, [
            tree.ReturnNode(tree.NumberNode(Token(token_kinds.number, "15")))
        ])  # yapf: disable

    def test_multiple_returns_in_main_function(self):  # noqa: D400, D403
        """int main() { return 15; return 10; }"""
        tokens = [
            Token(token_kinds.return_kw), Token(token_kinds.number, "15"),
            Token(token_kinds.semicolon), Token(token_kinds.return_kw),
            Token(token_kinds.number, "10"), Token(token_kinds.semicolon)
        ]

        self.assertParsesTo(tokens, [
            tree.ReturnNode(tree.NumberNode(Token(token_kinds.number, "15"))),
            tree.ReturnNode(tree.NumberNode(Token(token_kinds.number, "10")))
        ])  # yapf: disable

    def test_extra_tokens_at_end_after_main_function(self):  # noqa: D400, D403
        """int main() { return 15; } int"""
        tokens = [
            Token(token_kinds.int_kw), Token(token_kinds.main),
            Token(token_kinds.open_paren), Token(token_kinds.close_paren),
            Token(token_kinds.open_brack), Token(token_kinds.return_kw),
            Token(token_kinds.number, "15"), Token(token_kinds.semicolon),
            Token(token_kinds.close_brack), Token(token_kinds.int_kw)
        ]

        Parser(tokens).parse()
        self.assertIssues(["unexpected token at 'int'"])

    def test_missing_semicolon_and_end_brace(self):  # noqa: D400, D403
        """int main() { return 15"""
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren),
                  Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15")]

        Parser(tokens).parse()
        self.assertIssues(["expected semicolon after '15'"])

    def test_missing_semicolon_after_number(self):  # noqa: D400, D403
        """int main() { return 15 }"""
        tokens = [
            Token(token_kinds.return_kw), Token(token_kinds.number, "15")
        ]

        self.assertParserError(tokens, "expected semicolon after '15'")

    def test_missing_final_brace_main(self):  # noqa: D400, D403
        """int main() { return 15;"""
        tokens = [
            Token(token_kinds.int_kw), Token(token_kinds.main),
            Token(token_kinds.open_paren), Token(token_kinds.close_paren),
            Token(token_kinds.open_brack), Token(token_kinds.return_kw),
            Token(token_kinds.number, "15"), Token(token_kinds.semicolon)
        ]

        Parser(tokens).parse()
        self.assertIssues(["expected '}' after ';'"])

    def test_declaration_in_main(self):  # noqa: D400, D403
        """int main() { int var; }"""
        tokens = [Token(token_kinds.int_kw),
                  Token(token_kinds.identifier, "var"),
                  Token(token_kinds.semicolon)]
        self.assertParsesTo(tokens, [
            tree.DeclarationNode(Token(token_kinds.identifier, "var"),
                                 Token(token_kinds.int_kw), True)
        ])  # yapf: disable

    def test_equals_in_main(self):  # noqa: D400, D403
        """int main() { a = 10; }"""
        # This wouldn't compile, but it should still parse.
        tokens = [
            Token(token_kinds.identifier, "a"), Token(token_kinds.equals),
            Token(token_kinds.number, "10"), Token(token_kinds.semicolon)
        ]

        self.assertParsesTo(tokens, [
            tree.ExprStatementNode(
                tree.BinaryOperatorNode(
                    tree.IdentifierNode(Token(token_kinds.identifier, "a")),
                    Token(token_kinds.equals),
                    tree.NumberNode(Token(token_kinds.number, "10"))
                ))])  # yapf: disable

    def test_compound_statement(self):  # noqa: D400, D403
        """int main() { { return 15; return 20; } return 25; }"""
        tokens = [
            Token(token_kinds.open_brack), Token(token_kinds.return_kw),
            Token(token_kinds.number, "15"), Token(token_kinds.semicolon),
            Token(token_kinds.return_kw), Token(token_kinds.number, "20"),
            Token(token_kinds.semicolon), Token(token_kinds.close_brack),
            Token(token_kinds.return_kw), Token(token_kinds.number, "25"),
            Token(token_kinds.semicolon)
        ]

        self.assertParsesTo(tokens, [
            tree.CompoundNode([
                tree.ReturnNode(tree.NumberNode(
                    Token(token_kinds.number, "15"))),
                tree.ReturnNode(tree.NumberNode(
                    Token(token_kinds.number, "20")))
            ]),
            tree.ReturnNode(tree.NumberNode(Token(token_kinds.number, "25")))
        ])  # yapf: disable

    def test_one_line_if_statement(self):  # noqa: D400, D403
        """int main() { if(a) return 10; return 5; }"""
        tokens = [
            Token(token_kinds.if_kw), Token(token_kinds.open_paren),
            Token(token_kinds.identifier, "a"), Token(token_kinds.close_paren),
            Token(token_kinds.return_kw), Token(token_kinds.number, "10"),
            Token(token_kinds.semicolon), Token(token_kinds.return_kw),
            Token(token_kinds.number, "5"), Token(token_kinds.semicolon)
        ]

        self.assertParsesTo(tokens, [
            tree.IfStatementNode(
                tree.IdentifierNode(Token(token_kinds.identifier, "a")),
                tree.ReturnNode(tree.NumberNode(
                    Token(token_kinds.number, "10")))
            ),
            tree.ReturnNode(
                tree.NumberNode(Token(token_kinds.number, "5")))
        ])  # yapf: disable

    def test_compound_if_statement(self):  # noqa: D400, D403
        """int main() { if(a) {return 15; return 20;} return 25; }"""
        tokens = [
            Token(token_kinds.if_kw), Token(token_kinds.open_paren),
            Token(token_kinds.identifier, "a"), Token(token_kinds.close_paren),
            Token(token_kinds.open_brack), Token(token_kinds.return_kw),
            Token(token_kinds.number, "15"), Token(token_kinds.semicolon),
            Token(token_kinds.return_kw), Token(token_kinds.number, "20"),
            Token(token_kinds.semicolon), Token(token_kinds.close_brack),
            Token(token_kinds.return_kw), Token(token_kinds.number, "25"),
            Token(token_kinds.semicolon)
        ]

        self.assertParsesTo(tokens, [
            tree.IfStatementNode(
                tree.IdentifierNode(Token(token_kinds.identifier, "a")),
                tree.CompoundNode([
                    tree.ReturnNode(tree.NumberNode(
                        Token(token_kinds.number, "15"))),
                    tree.ReturnNode(tree.NumberNode(
                        Token(token_kinds.number, "20")))
                ])
            ),
            tree.ReturnNode(
                tree.NumberNode(Token(token_kinds.number, "25")))
        ])  # yapf: disable

    def test_missing_if_statement_open_paren(self):  # noqa: D400, D403
        """int main() { if a) {return 15;} }"""
        tokens = [
            Token(token_kinds.if_kw), Token(token_kinds.identifier, "a"),
            Token(token_kinds.close_paren), Token(token_kinds.return_kw),
            Token(token_kinds.number, "15"), Token(token_kinds.semicolon)
        ]

        self.assertParserError(tokens, "expected '(' after 'if'")

    def test_missing_if_statement_conditional(self):  # noqa: D400, D403
        """int main() { if () {return 15;} }"""
        tokens = [
            Token(token_kinds.if_kw), Token(token_kinds.open_paren),
            Token(token_kinds.close_paren), Token(token_kinds.return_kw),
            Token(token_kinds.number, "15"), Token(token_kinds.semicolon)
        ]

        self.assertParserError(tokens, "expected expression, got ')'")

    def test_missing_if_statement_close_paren(self):  # noqa: D400, D403
        """int main() { if (a {return 15;} }"""
        tokens = [
            Token(token_kinds.if_kw), Token(token_kinds.open_paren),
            Token(token_kinds.identifier, "a"), Token(token_kinds.return_kw),
            Token(token_kinds.number, "15"), Token(token_kinds.semicolon)
        ]

        self.assertParserError(tokens, "expected ')' after 'a'")


class ExpressionTests(ParserTestUtil):
    """Tests expression parsing."""

    def assertExprParsesTo(self, tokens, node):
        """Assert the given tokens are an expression that parses to node.

        The given tokens should be just the expression; no semicolon or
        whatnot.

        """
        tokens += [Token(token_kinds.semicolon)]
        node = tree.ExprStatementNode(node)
        self.assertParsesTo(tokens, [node])

    def test_sum_associative(self):  # noqa: D400, D403
        """15 + 10 + 5"""
        tokens = [Token(token_kinds.number, "1"), Token(token_kinds.plus),
                  Token(token_kinds.number, "2"), Token(token_kinds.plus),
                  Token(token_kinds.number, "3")]
        self.assertExprParsesTo(tokens, tree.BinaryOperatorNode(
            tree.BinaryOperatorNode(
                tree.NumberNode(Token(token_kinds.number, "1")),
                Token(token_kinds.plus),
                tree.NumberNode(Token(token_kinds.number, "2")), ),
            Token(token_kinds.plus),
            tree.NumberNode(Token(token_kinds.number, "3"))))  # disable: yapf

    def test_product_associative(self):  # noqa: D400, D403
        """1 * 2 * 3"""
        tokens = [Token(token_kinds.number, "1"), Token(token_kinds.star),
                  Token(token_kinds.number, "2"), Token(token_kinds.star),
                  Token(token_kinds.number, "3")]
        self.assertExprParsesTo(tokens, tree.BinaryOperatorNode(
            tree.BinaryOperatorNode(
                tree.NumberNode(Token(token_kinds.number, "1")),
                Token(token_kinds.star),
                tree.NumberNode(Token(token_kinds.number, "2")), ),
            Token(token_kinds.star),
            tree.NumberNode(Token(token_kinds.number, "3"))))  # disable: yapf

    def test_product_sum_order_of_operations(self):  # noqa: D400, D403
        """15 * 10 + 5 * 0"""
        tokens = [Token(token_kinds.number, "15"), Token(token_kinds.star),
                  Token(token_kinds.number, "10"), Token(token_kinds.plus),
                  Token(token_kinds.number, "5"), Token(token_kinds.star),
                  Token(token_kinds.number, "0")]

        # yapf: disable
        self.assertExprParsesTo(tokens, tree.BinaryOperatorNode(
            tree.BinaryOperatorNode(
                tree.NumberNode(Token(token_kinds.number, "15")),
                Token(token_kinds.star),
                tree.NumberNode(Token(token_kinds.number, "10"))),
            Token(token_kinds.plus),
            tree.BinaryOperatorNode(
                tree.NumberNode(Token(token_kinds.number, "5")),
                Token(token_kinds.star),
                tree.NumberNode(Token(token_kinds.number, "0")))))
        # yapf: enable

    def test_div_sum_order_of_operations(self):  # noqa: D400, D403
        """15 / 10 + 5 / 1"""
        tokens = [Token(token_kinds.number, "15"), Token(token_kinds.slash),
                  Token(token_kinds.number, "10"), Token(token_kinds.plus),
                  Token(token_kinds.number, "5"), Token(token_kinds.slash),
                  Token(token_kinds.number, "1")]

        self.assertExprParsesTo(tokens, tree.BinaryOperatorNode(
            tree.BinaryOperatorNode(
                tree.NumberNode(Token(token_kinds.number, "15")),
                Token(token_kinds.slash),
                tree.NumberNode(Token(token_kinds.number, "10"))),
            Token(token_kinds.plus),
            tree.BinaryOperatorNode(
                tree.NumberNode(Token(token_kinds.number, "5")),
                Token(token_kinds.slash),
                tree.NumberNode(Token(token_kinds.number, "1")))))

    def test_equals_right_associative(self):  # noqa: D400, D403
        """a = b = 10"""
        tokens = [Token(token_kinds.identifier, "a"),
                  Token(token_kinds.equals),
                  Token(token_kinds.identifier, "b"),
                  Token(token_kinds.equals), Token(token_kinds.number, "10")]

        # yapf: disable
        self.assertExprParsesTo(tokens, tree.BinaryOperatorNode(
            tree.IdentifierNode(Token(token_kinds.identifier, "a")),
            Token(token_kinds.equals),
            tree.BinaryOperatorNode(
                tree.IdentifierNode(Token(token_kinds.identifier, "b")),
                Token(token_kinds.equals),
                tree.NumberNode(Token(token_kinds.number, "10")))))
        # yapf: enable

    def test_equals_precedence_with_plus(self):  # noqa: D400, D403
        """a = b + 10"""
        tokens = [Token(token_kinds.identifier, "a"),
                  Token(token_kinds.equals),
                  Token(token_kinds.identifier, "b"), Token(token_kinds.plus),
                  Token(token_kinds.number, "10")]

        # yapf: disable
        self.assertExprParsesTo(tokens, tree.BinaryOperatorNode(
            tree.IdentifierNode(Token(token_kinds.identifier, "a")),
            Token(token_kinds.equals),
            tree.BinaryOperatorNode(
                tree.IdentifierNode(Token(token_kinds.identifier, "b")),
                Token(token_kinds.plus),
                tree.NumberNode(Token(token_kinds.number, "10")))))
        # yapf: enable

    def test_parens(self):  # noqa: D400, D403
        """5 + (10 + 15) + 20"""
        tokens = [Token(token_kinds.number, "5"), Token(token_kinds.plus),
                  Token(token_kinds.open_paren),
                  Token(token_kinds.number, "10"), Token(token_kinds.plus),
                  Token(token_kinds.number, "15"),
                  Token(token_kinds.close_paren), Token(token_kinds.plus),
                  Token(token_kinds.number, "20")]

        self.assertExprParsesTo(tokens, tree.BinaryOperatorNode(
            tree.BinaryOperatorNode(
                tree.NumberNode(Token(token_kinds.number, "5")),
                Token(token_kinds.plus),
                tree.ParenExprNode(
                    tree.BinaryOperatorNode(
                        tree.NumberNode(Token(token_kinds.number, "10")),
                        Token(token_kinds.plus),
                        tree.NumberNode(Token(token_kinds.number, "15"))))),
            Token(token_kinds.plus),
            tree.NumberNode(Token(token_kinds.number, "20"))))  # yapf: disable

    def test_two_equals(self):  # noqa: D400, D403
        """a == b + 10"""
        tokens = [Token(token_kinds.identifier, "a"),
                  Token(token_kinds.twoequals),
                  Token(token_kinds.identifier, "b"), Token(token_kinds.plus),
                  Token(token_kinds.number, "10")]

        self.assertExprParsesTo(tokens, tree.BinaryOperatorNode(
            tree.IdentifierNode(Token(token_kinds.identifier, "a")),
            Token(token_kinds.twoequals),
            tree.BinaryOperatorNode(
                tree.IdentifierNode(Token(token_kinds.identifier, "b")),
                Token(token_kinds.plus),
                tree.NumberNode(Token(token_kinds.number, "10")))))


class DeclarationTests(ParserTestUtil):
    """Tests declaration parsing."""

    def test_basic_int_declaration(self):  # noqa: D400, D403
        """int var;"""
        tokens = [Token(token_kinds.int_kw),
                  Token(token_kinds.identifier, "var"),
                  Token(token_kinds.semicolon)]
        self.assertParsesTo(tokens, [
            tree.DeclarationNode(Token(token_kinds.identifier, "var"),
                                 Token(token_kinds.int_kw), True)
        ])


    def test_basic_char_declaration(self):  # noqa: D400, D403
        """char var;"""
        tokens = [Token(token_kinds.char_kw),
                  Token(token_kinds.identifier, "var"),
                  Token(token_kinds.semicolon)]
        self.assertParsesTo(tokens, [
            tree.DeclarationNode(Token(token_kinds.identifier, "var"),
                                 Token(token_kinds.char_kw), True)
        ])  # yapf: disable

    def test_unsigned_int_declaration(self):  # noqa: D400, D403
        """unsigned int var;"""
        tokens = [Token(token_kinds.unsigned_kw),
                  Token(token_kinds.int_kw),
                  Token(token_kinds.identifier, "var"),
                  Token(token_kinds.semicolon)]
        self.assertParsesTo(tokens, [
            tree.DeclarationNode(Token(token_kinds.identifier, "var"),
                                 Token(token_kinds.int_kw), False)
        ])


    def test_unsigned_char_declaration(self):  # noqa: D400, D403
        """unsigned char var;"""
        tokens = [Token(token_kinds.unsigned_kw),
                  Token(token_kinds.char_kw),
                  Token(token_kinds.identifier, "var"),
                  Token(token_kinds.semicolon)]
        self.assertParsesTo(tokens, [
            tree.DeclarationNode(Token(token_kinds.identifier, "var"),
                                 Token(token_kinds.char_kw), False)
        ])  # yapf: disable

    def test_signed_int_declaration(self):  # noqa: D400, D403
        """signed int var;"""
        tokens = [Token(token_kinds.signed_kw),
                  Token(token_kinds.char_kw),
                  Token(token_kinds.identifier, "var"),
                  Token(token_kinds.semicolon)]
        self.assertParsesTo(tokens, [
            tree.DeclarationNode(Token(token_kinds.identifier, "var"),
                                 Token(token_kinds.char_kw), True)
        ])  # yapf: disable

    def test_signed_char_declaration(self):  # noqa: D400, D403
        """signed char var;"""
        tokens = [Token(token_kinds.signed_kw),
                  Token(token_kinds.char_kw),
                  Token(token_kinds.identifier, "var"),
                  Token(token_kinds.semicolon)]
        self.assertParsesTo(tokens, [
            tree.DeclarationNode(Token(token_kinds.identifier, "var"),
                                 Token(token_kinds.char_kw), True)
        ])  # yapf: disable

if __name__ == "__main__":
    unittest.main()
