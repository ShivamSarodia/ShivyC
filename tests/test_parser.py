"""Implements tests for the Parser class

"""
import unittest

import ast
from errors import CompilerError
from parser import Parser
import token_kinds
from tokens import Token

class GeneralTests(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()

    def test_main_function(self):
        """ int main() { return 15; } """
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren), Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15"), Token(token_kinds.semicolon),
                  Token(token_kinds.close_brack)]

        ast_root = self.parser.parse(tokens)
        self.assertEqual(ast_root,
                         ast.MainNode(
                             [ast.ReturnNode(
                                 ast.NumberNode(Token(token_kinds.number, "15"))
                             )]
                         ))
        
    def test_multiple_returns_in_main_function(self):
        """ int main() { return 15; return 10; } """
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren), Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack),
                  Token(token_kinds.return_kw), Token(token_kinds.number, "15"),
                  Token(token_kinds.semicolon),
                  Token(token_kinds.return_kw), Token(token_kinds.number, "10"),
                  Token(token_kinds.semicolon),
                  Token(token_kinds.close_brack)]

        ast_root = self.parser.parse(tokens)
        self.assertEqual(ast_root,
                         ast.MainNode(
                             [ast.ReturnNode(
                                 ast.NumberNode(Token(token_kinds.number, "15"))
                             ), ast.ReturnNode(
                                 ast.NumberNode(Token(token_kinds.number, "10"))
                             )]
                         ))
        
    def test_extra_tokens_at_end_after_main_function(self):
        """ int main() { return 15; } int """
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren), Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15"), Token(token_kinds.semicolon),
                  Token(token_kinds.close_brack), Token(token_kinds.int_kw)]
        with self.assertRaisesRegex(CompilerError, "unexpected token at 'int'"):
            ast_root = self.parser.parse(tokens)

    def test_missing_end_of_main_function_after_number(self):
        """ int main() { return 15 """
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren), Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15")]
        with self.assertRaisesRegex(CompilerError,
                                    "expected semicolon after '15'"):
            ast_root = self.parser.parse(tokens)

    def test_missing_semicolon_after_number(self):
        """ int main() { return 15 } """
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren), Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15"),
                  Token(token_kinds.close_brack)]
        with self.assertRaisesRegex(CompilerError,
                                    "expected semicolon after '15'"):
            ast_root = self.parser.parse(tokens)
            
    def test_missing_final_brace_main(self):
        """ int main() { return 15; """
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren), Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15"), Token(token_kinds.semicolon)]
        with self.assertRaisesRegex(
                CompilerError,
                "expected closing brace after ';'"):
            ast_root = self.parser.parse(tokens)

    def test_declaration_in_main(self):
        """ int main() { int var; }"""
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren), Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.int_kw),
                  Token(token_kinds.identifier, "var"),
                  Token(token_kinds.semicolon), Token(token_kinds.close_brack)]

        ast_root = self.parser.parse(tokens)
        self.assertEqual(ast_root,
                         ast.MainNode(
                             [ast.DeclarationNode(
                                 Token(token_kinds.identifier, "var"))]))

    def test_equals_in_main(self):
        """ int main() { a = 10; } """
        # This wouldn't compile, but it should still parse.
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren), Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack),
                  Token(token_kinds.identifier, "a"), Token(token_kinds.equals),
                  Token(token_kinds.number, "10"),
                  Token(token_kinds.semicolon), Token(token_kinds.close_brack)]

        ast_root = self.parser.parse(tokens)
        self.assertEqual(ast_root,
                         ast.MainNode(
                             [ast.BinaryOperatorNode(
                                 ast.IdentifierNode(
                                     Token(token_kinds.identifier, "a")),
                                 Token(token_kinds.equals),
                                 ast.NumberNode(
                                     Token(token_kinds.number, "10")))
                             ]))

class ExpressionTests(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()

    def test_sum_associative(self):
        """ 15 + 10 + 5 """
        tokens = [Token(token_kinds.number, "1"), Token(token_kinds.plus),
                  Token(token_kinds.number, "2"), Token(token_kinds.plus),
                  Token(token_kinds.number, "3")]

        ast_root = self.parser.expect_expression(tokens, 0)[0]
        self.assertEqual(ast_root,
                         ast.BinaryOperatorNode(
                             ast.BinaryOperatorNode(
                                 ast.NumberNode(Token(token_kinds.number, "1")),
                                 Token(token_kinds.plus),
                                 ast.NumberNode(Token(token_kinds.number, "2")),
                             ),
                             Token(token_kinds.plus),
                             ast.NumberNode(Token(token_kinds.number, "3"))
                         ))

    def test_product_associative(self):
        """ 1 * 2 * 3 """
        tokens = [Token(token_kinds.number, "1"), Token(token_kinds.plus),
                  Token(token_kinds.number, "2"), Token(token_kinds.plus),
                  Token(token_kinds.number, "3")]

        ast_root = self.parser.expect_expression(tokens, 0)[0]
        self.assertEqual(ast_root,
                         ast.BinaryOperatorNode(
                             ast.BinaryOperatorNode(
                                 ast.NumberNode(Token(token_kinds.number, "1")),
                                 Token(token_kinds.plus),
                                 ast.NumberNode(Token(token_kinds.number, "2")),
                             ),
                             Token(token_kinds.plus),
                             ast.NumberNode(Token(token_kinds.number, "3"))
                         ))

    def test_product_sum_order_of_operations(self):
        tokens = [Token(token_kinds.number, "15"), Token(token_kinds.star),
                  Token(token_kinds.number, "10"), Token(token_kinds.plus),
                  Token(token_kinds.number, "5"), Token(token_kinds.star),
                  Token(token_kinds.number, "0")]

        ast_root = self.parser.expect_expression(tokens, 0)[0]
        self.assertEqual(ast_root,
                         ast.BinaryOperatorNode(
                             ast.BinaryOperatorNode(
                                 ast.NumberNode(
                                     Token(token_kinds.number, "15")),
                                 Token(token_kinds.star),
                                 ast.NumberNode(
                                     Token(token_kinds.number, "10"))
                             ),
                             Token(token_kinds.plus),
                             ast.BinaryOperatorNode(
                                 ast.NumberNode(
                                     Token(token_kinds.number, "5")),
                                 Token(token_kinds.star),
                                 ast.NumberNode(
                                     Token(token_kinds.number, "0"))
                             )
                         ))

    def test_equals_right_associative(self):
        tokens = [Token(token_kinds.identifier, "a"), Token(token_kinds.equals),
                  Token(token_kinds.identifier, "b"), Token(token_kinds.equals),
                  Token(token_kinds.number, "10")]

        ast_root = self.parser.expect_expression(tokens, 0)[0]
        self.assertEqual(ast_root,
                         ast.BinaryOperatorNode(
                             ast.IdentifierNode(
                                 Token(token_kinds.identifier, "a")),
                             Token(token_kinds.equals),
                             ast.BinaryOperatorNode(
                                 ast.IdentifierNode(
                                     Token(token_kinds.identifier, "b")),
                                 Token(token_kinds.equals),
                                 ast.NumberNode(Token(token_kinds.number, "10"))
                             )
                         ))

    def test_equals_precedence_with_plus(self):
        tokens = [Token(token_kinds.identifier, "a"), Token(token_kinds.equals),
                  Token(token_kinds.identifier, "b"), Token(token_kinds.plus),
                  Token(token_kinds.number, "10")]

        ast_root = self.parser.expect_expression(tokens, 0)[0]
        self.assertEqual(ast_root,
                         ast.BinaryOperatorNode(
                             ast.IdentifierNode(
                                 Token(token_kinds.identifier, "a")),
                             Token(token_kinds.equals),
                             ast.BinaryOperatorNode(
                                 ast.IdentifierNode(
                                     Token(token_kinds.identifier, "b")),
                                 Token(token_kinds.plus),
                                 ast.NumberNode(Token(token_kinds.number, "10"))
                             )
                         ))
        
class DeclarationTests(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()
        
    def test_basic_declaration(self):
        tokens = [Token(token_kinds.int_kw),
                  Token(token_kinds.identifier, "var"),
                  Token(token_kinds.semicolon)]
        ast_root = self.parser.expect_declaration(tokens, 0)[0]
        self.assertEqual(ast_root,
                         ast.DeclarationNode(
                             Token(token_kinds.identifier, "var")))

if __name__ == "__main__":
    unittest.main()
