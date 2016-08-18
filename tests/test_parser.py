"""Tests for the parser phase of the compiler."""

import unittest

import tree
import token_kinds
from errors import CompilerError
from parser import Parser
from tokens import Token


class GeneralTests(unittest.TestCase):
    """General tests of the parser."""

    def test_main_function(self):  # noqa: D400, D403
        """int main() { return 15; }"""
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren),
                  Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15"),
                  Token(token_kinds.semicolon), Token(token_kinds.close_brack)]

        ast_root = Parser(tokens).parse()
        self.assertEqual(ast_root, tree.MainNode([
            tree.ReturnNode(tree.NumberNode(Token(token_kinds.number, "15")))
        ]))

    def test_multiple_returns_in_main_function(self):  # noqa: D400, D403
        """int main() { return 15; return 10; }"""
        tokens = [
            Token(token_kinds.int_kw), Token(token_kinds.main),
            Token(token_kinds.open_paren), Token(token_kinds.close_paren),
            Token(token_kinds.open_brack), Token(token_kinds.return_kw),
            Token(token_kinds.number, "15"), Token(token_kinds.semicolon),
            Token(token_kinds.return_kw), Token(token_kinds.number, "10"),
            Token(token_kinds.semicolon), Token(token_kinds.close_brack)
        ]

        ast_root = Parser(tokens).parse()
        self.assertEqual(ast_root, tree.MainNode([
            tree.ReturnNode(tree.NumberNode(Token(token_kinds.number, "15"))),
            tree.ReturnNode(tree.NumberNode(Token(token_kinds.number, "10")))
        ]))

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
            Token(token_kinds.int_kw), Token(token_kinds.main),
            Token(token_kinds.open_paren), Token(token_kinds.close_paren),
            Token(token_kinds.open_brack), Token(token_kinds.return_kw),
            Token(token_kinds.number, "15"), Token(token_kinds.close_brack)
        ]
        with self.assertRaisesRegex(CompilerError,
                                    "expected semicolon after '15'"):
            Parser(tokens).parse()

    def test_missing_final_brace_main(self):  # noqa: D400, D403
        """int main() { return 15;"""
        tokens = [
            Token(token_kinds.int_kw), Token(token_kinds.main),
            Token(token_kinds.open_paren), Token(token_kinds.close_paren),
            Token(token_kinds.open_brack), Token(token_kinds.return_kw),
            Token(token_kinds.number, "15"), Token(token_kinds.semicolon)
        ]
        with self.assertRaisesRegex(CompilerError,
                                    "expected closing brace after ';'"):
            Parser(tokens).parse()

    def test_declaration_in_main(self):  # noqa: D400, D403
        """int main() { int var; }"""
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren),
                  Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.int_kw),
                  Token(token_kinds.identifier, "var"),
                  Token(token_kinds.semicolon), Token(token_kinds.close_brack)]

        ast_root = Parser(tokens).parse()
        self.assertEqual(ast_root, tree.MainNode(
            [tree.DeclarationNode(Token(token_kinds.identifier, "var"))]))

    def test_equals_in_main(self):  # noqa: D400, D403
        """int main() { a = 10; }"""
        # This wouldn't compile, but it should still parse.
        tokens = [
            Token(token_kinds.int_kw), Token(token_kinds.main),
            Token(token_kinds.open_paren), Token(token_kinds.close_paren),
            Token(token_kinds.open_brack), Token(token_kinds.identifier, "a"),
            Token(token_kinds.equals), Token(token_kinds.number, "10"),
            Token(token_kinds.semicolon), Token(token_kinds.close_brack)
        ]

        ast_root = Parser(tokens).parse()
        self.assertEqual(ast_root, tree.MainNode([tree.ExprStatementNode(
            tree.BinaryOperatorNode(
                tree.IdentifierNode(Token(token_kinds.identifier, "a")),
                Token(token_kinds.equals),
                tree.NumberNode(Token(token_kinds.number, "10"))
            ))]))  # yapf: disable

    def test_one_line_if_statement(self):  # noqa: D400, D403
        """int main() { if(a) return 10; return 5; }"""
        tokens = [
            Token(token_kinds.int_kw), Token(token_kinds.main),
            Token(token_kinds.open_paren), Token(token_kinds.close_paren),
            Token(token_kinds.open_brack), Token(token_kinds.if_kw),
            Token(token_kinds.open_paren), Token(token_kinds.identifier, "a"),
            Token(token_kinds.close_paren), Token(token_kinds.return_kw),
            Token(token_kinds.number, "10"), Token(token_kinds.semicolon),
            Token(token_kinds.return_kw), Token(token_kinds.number, "5"),
            Token(token_kinds.semicolon), Token(token_kinds.close_brack)
        ]

        ast_root = Parser(tokens).parse()
        self.assertEqual(ast_root, tree.MainNode([
            tree.IfStatementNode(
                tree.IdentifierNode(Token(token_kinds.identifier, "a")),
                tree.ReturnNode(tree.NumberNode(
                    Token(token_kinds.number, "10")))
            ),
            tree.ReturnNode(tree.NumberNode(Token(token_kinds.number, "5")))
        ]))  # yapf: disable


class ExpressionTests(unittest.TestCase):
    """Tests expression parsing.

    TODO: Change these tests to use Parser.parse() directly.

    """

    def test_sum_associative(self):  # noqa: D400, D403
        """15 + 10 + 5"""
        tokens = [Token(token_kinds.number, "1"), Token(token_kinds.plus),
                  Token(token_kinds.number, "2"), Token(token_kinds.plus),
                  Token(token_kinds.number, "3")]

        ast_root = Parser(tokens).parse_expression(0)[0]
        self.assertEqual(ast_root, tree.BinaryOperatorNode(
            tree.BinaryOperatorNode(
                tree.NumberNode(Token(token_kinds.number, "1")),
                Token(token_kinds.plus),
                tree.NumberNode(Token(token_kinds.number, "2")), ),
            Token(token_kinds.plus),
            tree.NumberNode(Token(token_kinds.number, "3"))))  # yapf: disable

    def test_product_associative(self):  # noqa: D400, D403
        """1 * 2 * 3"""
        tokens = [Token(token_kinds.number, "1"), Token(token_kinds.plus),
                  Token(token_kinds.number, "2"), Token(token_kinds.plus),
                  Token(token_kinds.number, "3")]

        ast_root = Parser(tokens).parse_expression(0)[0]
        self.assertEqual(ast_root, tree.BinaryOperatorNode(
            tree.BinaryOperatorNode(
                tree.NumberNode(Token(token_kinds.number, "1")),
                Token(token_kinds.plus),
                tree.NumberNode(Token(token_kinds.number, "2")), ),
            Token(token_kinds.plus),
            tree.NumberNode(Token(token_kinds.number, "3"))))  # yapf: disable

    def test_product_sum_order_of_operations(self):  # noqa: D400, D403
        """15 * 10 + 5 * 0"""
        tokens = [Token(token_kinds.number, "15"), Token(token_kinds.star),
                  Token(token_kinds.number, "10"), Token(token_kinds.plus),
                  Token(token_kinds.number, "5"), Token(token_kinds.star),
                  Token(token_kinds.number, "0")]

        ast_root = Parser(tokens).parse_expression(0)[0]
        # yapf: disable
        self.assertEqual(ast_root, tree.BinaryOperatorNode(
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

        ast_root = Parser(tokens).parse_expression(0)[0]
        # yapf: disable
        self.assertEqual(ast_root, tree.BinaryOperatorNode(
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

        ast_root = Parser(tokens).parse_expression(0)[0]
        # yapf: disable
        self.assertEqual(ast_root, tree.BinaryOperatorNode(
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

        ast_root = Parser(tokens).parse_expression(0)[0]
        self.assertEqual(ast_root, tree.BinaryOperatorNode(
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


class DeclarationTests(unittest.TestCase):
    """Tests declaration parsing.

    TODO: Change these tests to use Parser.parse() directly.

    """

    def test_basic_declaration(self):  # noqa: D400, D403
        """int var;"""
        tokens = [Token(token_kinds.int_kw),
                  Token(token_kinds.identifier, "var"),
                  Token(token_kinds.semicolon)]
        ast_root = Parser(tokens).parse_declaration(0)[0]
        # yapf: enable
        self.assertEqual(
            ast_root,
            tree.DeclarationNode(Token(token_kinds.identifier, "var")))
        # yapf: disable


if __name__ == "__main__":
    unittest.main()
