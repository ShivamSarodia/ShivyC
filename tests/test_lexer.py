"""Tests for the lexer phase of the compiler."""

import unittest

import token_kinds
from errors import CompilerError
from lexer import Lexer
from tokens import Token
from tokens import TokenKind


class LexerArtificialTests(unittest.TestCase):
    """Tests the lexer on artificial token kinds."""

    def setUp(self):
        """Define abstract token kinds that allow testing lexer edge cases."""
        self.keyword_kinds = []
        self.symbol_kinds = []
        self.tok = TokenKind("tok", self.keyword_kinds)
        self.token = TokenKind("token", self.keyword_kinds)
        self.apple = TokenKind("apple", self.symbol_kinds)
        self.app = TokenKind("app", self.symbol_kinds)

        self.lexer = Lexer(self.symbol_kinds, self.keyword_kinds)

    def test_token_kinds_are_unequal(self):
        """Test that different token kinds do not evaluate equal."""
        self.assertFalse(self.tok == self.token)
        self.assertFalse(self.tok == self.apple)
        self.assertFalse(self.tok == self.app)
        self.assertFalse(self.token == self.apple)
        self.assertFalse(self.token == self.app)
        self.assertFalse(self.apple == self.app)

    def test_empty_content(self):
        """Test empty content tokenizes to an empty list."""
        self.assertEqual(self.lexer.tokenize_line(""), [])

    def test_one_keyword(self):
        """Test content with one keyword token kind."""
        self.assertEqual(self.lexer.tokenize_line("tok"), [Token(self.tok)])

    def test_one_long_keyword(self):
        """Test tokenizing keyword that contains another keyword."""
        self.assertEqual(
            self.lexer.tokenize_line("token"), [Token(self.token)])

    def test_multiple_keywords(self):
        """Test tokenizing multiple keywords."""
        content = "tok token tok tok token"
        tokens = [Token(self.tok), Token(self.token), Token(self.tok),
                  Token(self.tok), Token(self.token)]
        self.assertEqual(self.lexer.tokenize_line(content), tokens)

    def test_keywords_without_space_as_identifier(self):
        """Test keywords without space do not get split."""
        self.assertEqual(
            self.lexer.tokenize_line("toktoken"),
            [Token(token_kinds.identifier, "toktoken")])

    def test_keywords_with_extra_whitespace(self):
        """Test keywords with extra whitespace still get split."""
        content = "  tok  token  tok  tok  token  "
        tokens = [Token(self.tok), Token(self.token), Token(self.tok),
                  Token(self.tok), Token(self.token)]
        self.assertEqual(self.lexer.tokenize_line(content), tokens)

    def test_one_symbol(self):
        """Test tokenizing one symbol alone."""
        self.assertEqual(self.lexer.tokenize_line("app"), [Token(self.app)])

    def test_one_long_symbol(self):
        """Test tokenizing one symbol that contains another symbol."""
        self.assertEqual(
            self.lexer.tokenize_line("apple"), [Token(self.apple)])

    def test_symbol_splits_keywords(self):
        """Test tokenizing a symbol between keywords."""
        self.assertEqual(
            self.lexer.tokenize_line("tokenapptok"),
            [Token(self.token), Token(self.app), Token(self.tok)])

    def test_multiple_symbols(self):
        """Test tokenizing a tough group of keywords."""
        content = "appleappappappleapp"
        tokens = [Token(self.apple), Token(self.app), Token(self.app),
                  Token(self.apple), Token(self.app)]
        self.assertEqual(self.lexer.tokenize_line(content), tokens)

    def test_symbols_with_extra_whitespace(self):
        """Test tokenizing a tough group of keywords with spaces."""
        content = "   apple appapp apple    app  "
        tokens = [Token(self.apple), Token(self.app), Token(self.app),
                  Token(self.apple), Token(self.app)]
        self.assertEqual(self.lexer.tokenize_line(content), tokens)


class LexerConcreteTests(unittest.TestCase):
    """Tests the lexer on the actual token kinds (see token_kinds.py)."""

    def setUp(self):
        """Set up lexer with the token kinds from token_kinds.py."""
        self.lexer = Lexer(token_kinds.symbol_kinds, token_kinds.keyword_kinds)

    def test_number(self):
        """Test tokenizing a single number."""
        self.assertEqual(
            self.lexer.tokenize_line("10"), [Token(token_kinds.number, "10")])

    def test_easy_identifier(self):
        """Test tokenizing an identifier with only letters."""
        self.assertEqual(
            self.lexer.tokenize_line("identifier"),
            [Token(token_kinds.identifier, "identifier")])

    def test_hard_identifier(self):
        """Test tokenizing an identifier symbols."""
        self.assertEqual(
            self.lexer.tokenize_line("_ident123ifier"),
            [Token(token_kinds.identifier, "_ident123ifier")])

    def test_bad_identifier(self):
        """Test error on tokenizing an identifier starting with digit."""
        with self.assertRaisesRegex(CompilerError,
                                    "unrecognized token at '1identifier'"):
            self.lexer.tokenize_line("1identifier")

    def test_basic_program_one_line(self):
        """Test tokenizing an entire basic program that is one line."""
        content = "int main() { return 15; }"
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren),
                  Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15"),
                  Token(token_kinds.semicolon), Token(token_kinds.close_brack)]
        self.assertEqual(self.lexer.tokenize_line(content), tokens)

    def test_basic_program_multi_line(self):
        """Test tokenizing an entire basic program that is multiple lines."""
        content = [("int main()", "main.c", 1), ("{", "main.c", 2),
                   ("return 15;", "main.c", 3), ("}", "main.c", 4)]
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren),
                  Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15"),
                  Token(token_kinds.semicolon), Token(token_kinds.close_brack)]
        self.assertEqual(self.lexer.tokenize(content), tokens)


if __name__ == "__main__":
    unittest.main()
