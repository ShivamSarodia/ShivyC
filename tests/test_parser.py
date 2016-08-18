"""Tests for the parser phase of the compiler."""

import unittest

import tree
import token_kinds
from errors import CompilerError
from parser import Parser
from tokens import Token


class ParserTestUtil(unittest.TestCase):
    """Utilities for parser tests."""

    def assertParsesTo(self, tokens, nodes):
        """Assert the given tokens parse to the given tree nodes.

        This method adds the 'int main() { }' so no need to include those
        tokens in the input list. Similarly, nodes need not include the
        tree.MainNode, just a list of the nodes within.

        """
        ast_root = Parser(self._token_wrap_main(tokens)).parse()
        self.assertEqual(ast_root, tree.MainNode(tree.CompoundNode(nodes)))

    def assertParserError(self, tokens, regex):
        """Assert the given tokens raise a compiler error during parsing.

        Expects the raised compiler error message to match the given regex.
        As above, no need to include 'int main() { }' in the tokens.

        """
        with self.assertRaisesRegex(CompilerError, regex):
            Parser(self._token_wrap_main(tokens)).parse()

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
        with self.assertRaisesRegex(CompilerError,
                                    "unexpected token at 'int'"):
            Parser(tokens).parse()

    def test_missing_semicolon_and_end_brace(self):  # noqa: D400, D403
        """int main() { return 15"""
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren),
                  Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15")]
        with self.assertRaisesRegex(CompilerError,
                                    "expected semicolon after '15'"):
            Parser(tokens).parse()

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
        with self.assertRaisesRegex(CompilerError, "expected '}' after ';'"):
            Parser(tokens).parse()

    def test_declaration_in_main(self):  # noqa: D400, D403
        """int main() { int var; }"""
        tokens = [Token(token_kinds.int_kw),
                  Token(token_kinds.identifier, "var"),
                  Token(token_kinds.semicolon)]
        self.assertParsesTo(tokens, [
            tree.DeclarationNode(Token(token_kinds.identifier, "var"))
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

        self.assertParserError(tokens, "expected '\(' after 'if'")

    def test_missing_if_statement_conditional(self):  # noqa: D400, D403
        """int main() { if () {return 15;} }"""
        tokens = [
            Token(token_kinds.if_kw), Token(token_kinds.open_paren),
            Token(token_kinds.close_paren), Token(token_kinds.return_kw),
            Token(token_kinds.number, "15"), Token(token_kinds.semicolon)
        ]

        self.assertParserError(tokens, "expected expression, got '\)'")

    def test_missing_if_statement_close_paren(self):  # noqa: D400, D403
        """int main() { if (a {return 15;} }"""
        tokens = [
            Token(token_kinds.if_kw), Token(token_kinds.open_paren),
            Token(token_kinds.identifier, "a"), Token(token_kinds.return_kw),
            Token(token_kinds.number, "15"), Token(token_kinds.semicolon)
        ]

        self.assertParserError(tokens, "expected '\)' after 'a'")


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


class DeclarationTests(ParserTestUtil):
    """Tests declaration parsing."""

    def test_basic_declaration(self):  # noqa: D400, D403
        """int var;"""
        tokens = [Token(token_kinds.int_kw),
                  Token(token_kinds.identifier, "var"),
                  Token(token_kinds.semicolon)]
        self.assertParsesTo(tokens, [
            tree.DeclarationNode(Token(token_kinds.identifier, "var"))
        ])


if __name__ == "__main__":
    unittest.main()
