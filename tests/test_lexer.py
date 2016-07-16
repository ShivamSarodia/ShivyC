"""Implements tests for the Lexer class

"""
import unittest

from errors import CompilerError
from lexer import Lexer
import token_kinds
from tokens import Token
from tokens import TokenKind

class lexer_pure_unit_tests(unittest.TestCase):
    def setUp(self):
        self.keyword_kinds = []
        self.symbol_kinds = []
        self.tok = TokenKind("tok", self.keyword_kinds)
        self.token = TokenKind("token", self.keyword_kinds)
        self.apple = TokenKind("apple", self.symbol_kinds)
        self.app = TokenKind("app", self.symbol_kinds)
        
        self.lexer = Lexer(self.symbol_kinds, self.keyword_kinds)

    def test_token_kinds_are_unequal(self):
        self.assertFalse(self.tok == self.token)
        self.assertFalse(self.tok == self.apple)
        self.assertFalse(self.tok == self.app)
        self.assertFalse(self.token == self.apple)
        self.assertFalse(self.token == self.app)
        self.assertFalse(self.apple == self.app)

    def test_empty_content(self):
        self.assertEqual(self.lexer.tokenize_line(""), [])
        
    def test_one_keyword(self):
        self.assertEqual(self.lexer.tokenize_line("tok"), [Token(self.tok)])

    def test_one_long_keyword(self):
        self.assertEqual(self.lexer.tokenize_line("token"), [Token(self.token)])

    def test_multiple_keywords(self):
        content = "tok token tok tok token"
        tokens = [Token(self.tok), Token(self.token), Token(self.tok),
                  Token(self.tok), Token(self.token)]
        self.assertEqual(self.lexer.tokenize_line(content), tokens)
        
    def test_keywords_without_space(self):
        with self.assertRaisesRegex(CompilerError, "unrecognized token"):
            self.lexer.tokenize_line("toktoken")

    def test_keywords_with_extra_whitespace(self):
        content = "  tok  token  tok  tok  token  "
        tokens = [Token(self.tok), Token(self.token), Token(self.tok),
                  Token(self.tok), Token(self.token)]
        self.assertEqual(self.lexer.tokenize_line(content), tokens)

    def test_one_symbol(self):
        self.assertEqual(self.lexer.tokenize_line("app"), [Token(self.app)])

    def test_one_long_symbol(self):
        self.assertEqual(self.lexer.tokenize_line("apple"), [Token(self.apple)])

    def test_symbol_splits_keywords(self):
        self.assertEqual(self.lexer.tokenize_line("tokenapptok"),
                         [Token(self.token), Token(self.app), Token(self.tok)])
        
    def test_multiple_symbols(self):
        content = "appleappappappleapp"
        tokens = [Token(self.apple), Token(self.app), Token(self.app),
                  Token(self.apple), Token(self.app)]
        self.assertEqual(self.lexer.tokenize_line(content), tokens)

    def test_symbols_with_extra_whitespace(self):
        content = "   apple appapp apple    app  "
        tokens = [Token(self.apple), Token(self.app), Token(self.app),
                  Token(self.apple), Token(self.app)]
        self.assertEqual(self.lexer.tokenize_line(content), tokens)

class lexer_integration_tests(unittest.TestCase):
    """Tests the lexer on the actual token_kinds, as defined in token_kinds.py

    """
    def setUp(self):
        self.lexer = Lexer(token_kinds.symbol_kinds, token_kinds.keyword_kinds)

    def test_number(self):
        self.assertEqual(self.lexer.tokenize_line("10"),
                         [Token(token_kinds.number, "10")])

    def test_basic_program_one_line(self):
        content = "int main() { return 15; }"
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren), Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15"), Token(token_kinds.semicolon),
                  Token(token_kinds.close_brack)]
        self.assertEqual(self.lexer.tokenize_line(content), tokens)

    def test_basic_program_multi_line(self):
        content = [("int main()", "main.c", 1),
                   ("{", "main.c", 2),
                   ("return 15;", "main.c", 3),
                   ("}", "main.c", 4)]
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren), Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15"), Token(token_kinds.semicolon),
                  Token(token_kinds.close_brack)]
        self.assertEqual(self.lexer.tokenize(content), tokens)
            
if __name__ == "__main__":
    unittest.main()
