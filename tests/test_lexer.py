"""Tests for the lexer phase of the compiler."""

import lexer
import token_kinds
from errors import error_collector
from tokens import Token
from tests.test_utils import TestUtils


class LexerTests(TestUtils):
    """Tests the lexer on the actual token kinds (see token_kinds.py)."""

    def setUp(self):
        """Set up lexer with the token kinds from token_kinds.py."""
        error_collector.clear()

    def test_empty(self):
        """Test tokenizing an empty string."""
        self.assertEqual(lexer.tokenize("", ""), [])

    def test_just_whitespace(self):
        """Test tokenizing a string of just whitespace."""
        self.assertEqual(lexer.tokenize("   ", ""), [])

    def test_number(self):
        """Test tokenizing a single number."""
        self.assertEqual(
            lexer.tokenize("10", ""), [Token(token_kinds.number, "10")])

    def test_easy_identifier(self):
        """Test tokenizing an identifier with only letters."""
        self.assertEqual(
            lexer.tokenize("identifier", ""),
            [Token(token_kinds.identifier, "identifier")])

    def test_hard_identifier(self):
        """Test tokenizing an identifier symbols."""
        self.assertEqual(
            lexer.tokenize("_ident123ifier", ""),
            [Token(token_kinds.identifier, "_ident123ifier")])

    def test_extra_whitespace(self):
        """Test tokenizing symbols with whitespace."""
        self.assertEqual(
            lexer.tokenize("  10    ident123ifier  ", ""),
            [Token(token_kinds.number, "10"),
             Token(token_kinds.identifier, "ident123ifier")])

    def test_symbol_splits_keywords(self):
        """Test that the lexer splits on symbols."""
        self.assertEqual(
            lexer.tokenize("ident1+ident2", ""),
            [Token(token_kinds.identifier, "ident1"),
             Token(token_kinds.plus),
             Token(token_kinds.identifier, "ident2")])

    def test_single_equals(self):
        """Test tokenizing single equals."""
        self.assertEqual(
            lexer.tokenize("a = 10", ""),
            [Token(token_kinds.identifier, "a"),
             Token(token_kinds.equals),
             Token(token_kinds.number, "10")])

    def test_double_equals(self):
        """Test tokenizing double equals."""
        self.assertEqual(
            lexer.tokenize("a == 10", ""),
            [Token(token_kinds.identifier, "a"),
             Token(token_kinds.twoequals),
             Token(token_kinds.number, "10")])

    def test_simple_string(self):
        """Test tokenizing simple string."""
        self.assertEqual(
            lexer.tokenize('a "ab"', ""),
            [Token(token_kinds.identifier, "a"),
             Token(token_kinds.string, [97, 98, 0])])

    def test_escapes(self):
        r"""Test tokenizing strings with escapes.

        This is testing the string:
        " \" \\ \n \\t "
        without the spaces.
        """
        self.assertEqual(
            lexer.tokenize(r'"\"\\\n\\t"', ""),
            [Token(token_kinds.string,
                   [ord('"'), ord("\\"), ord("\n"), ord("\\"), ord("t"), 0]
                   )])

    def test_missing_close_quote(self):
        """Test error on tokenizing an string missing close quotation."""
        lexer.tokenize("\"hello", "")
        self.assertIssues(["missing terminating double quote"])

    def test_bad_identifier(self):
        """Test error on tokenizing an identifier starting with digit."""
        lexer.tokenize("1identifier", "")
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
        self.assertEqual(lexer.tokenize(content, ""), tokens)

    def test_include(self):
        """Test tokenizing an include statement."""
        content = '#/*hi*/include/*hey*/"hello hi there/*\"//more comments'
        tokens = [Token(token_kinds.pound),
                  Token(token_kinds.identifier, "include"),
                  Token(token_kinds.include_file, '"hello hi there/*\"')]
        self.assertEqual(lexer.tokenize(content, ""), tokens)
