"""Implements tests for the Parser class

"""
import unittest

import ast
from parser import Parser
import token_kinds
from tokens import Token

class parser_tests(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()

    def test_parse_main(self):
        """ int main() { return 15; } """
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren), Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15"), Token(token_kinds.semicolon),
                  Token(token_kinds.close_brack)]

        ast_root = self.parser.parse(tokens)
        self.assertEqual(ast_root,
                         ast.MainNode(Token(token_kinds.number, "15")))

    def test_bad_parse_main(self):
        """ Missing semicolon: int main() { return 15 } """
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren), Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15"),
                  Token(token_kinds.close_brack)]
        
        with self.assertRaises(NotImplementedError):
            ast_root = self.parser.parse(tokens)

if __name__ == "__main__":
    unittest.main()
