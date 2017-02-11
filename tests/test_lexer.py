"""Tests for the lexer phase of the compiler."""

import unittest

import token_kinds
from errors import error_collector
from lexer import Lexer
from tokens import Token
from tests.test_utils import TestUtils


class LexerConcreteTests(TestUtils):
    """Tests the lexer on the actual token kinds (see token_kinds.py)."""

    def setUp(self):
        """Set up lexer with the token kinds from token_kinds.py."""
        error_collector.clear()

    def test_empty(self):
        """Test tokenizing an empty string."""
        self.assertEqual(Lexer().tokenize_line(""), [])

    def test_just_whitespace(self):
        """Test tokenizing a string of just whitespace."""
        self.assertEqual(Lexer().tokenize_line("   "), [])

    def test_number(self):
        """Test tokenizing a single number."""
        self.assertEqual(
            Lexer().tokenize_line("10"), [Token(token_kinds.number, "10")])

    def test_easy_identifier(self):
        """Test tokenizing an identifier with only letters."""
        self.assertEqual(
            Lexer().tokenize_line("identifier"),
            [Token(token_kinds.identifier, "identifier")])

    def test_hard_identifier(self):
        """Test tokenizing an identifier symbols."""
        self.assertEqual(
            Lexer().tokenize_line("_ident123ifier"),
            [Token(token_kinds.identifier, "_ident123ifier")])

    def test_extra_whitespace(self):
        """Test tokenizing symbols with whitespace."""
        self.assertEqual(
            Lexer().tokenize_line("  10    ident123ifier  "),
            [Token(token_kinds.number, "10"),
             Token(token_kinds.identifier, "ident123ifier")])

    def test_symbol_splits_keywords(self):
        """Test that the lexer splits on symbols."""
        self.assertEqual(
            Lexer().tokenize_line("ident1+ident2"),
            [Token(token_kinds.identifier, "ident1"),
             Token(token_kinds.plus),
             Token(token_kinds.identifier, "ident2")])

    def test_bad_identifier(self):
        """Test error on tokenizing an identifier starting with digit."""
        Lexer().tokenize_line("1identifier")
        self.assertIssues(["unrecognized token at '1identifier'"])

    def test_basic_program_one_line(self):
        """Test tokenizing an entire basic program that is one line."""
        content = "int main() { return 15; }"
        tokens = [Token(token_kinds.int_kw), Token(token_kinds.main),
                  Token(token_kinds.open_paren),
                  Token(token_kinds.close_paren),
                  Token(token_kinds.open_brack), Token(token_kinds.return_kw),
                  Token(token_kinds.number, "15"),
                  Token(token_kinds.semicolon), Token(token_kinds.close_brack)]
        self.assertEqual(Lexer().tokenize_line(content), tokens)

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
        self.assertEqual(Lexer().tokenize(content), tokens)


if __name__ == "__main__":
    unittest.main()
