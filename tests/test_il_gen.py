"""Tests for the AST->IL phase of the compiler."""

import unittest

import il_commands
from errors import error_collector
from il_gen import ILCode
from il_gen import SymbolTable
from lexer import Lexer
from parser import Parser
from tests.test_utils import TestUtils


class ILGenTests(TestUtils):
    """Tests for the AST->IL phase of the compiler.

    We're lowkey cheating here--these are more of integration tests than unit
    tests, because we're also tokenizing/parsing the input string. However,
    writing out the parsed form for every test is a lot of struggle that's not
    really worth it given that we have good tests of the parsing phase
    anyway.

    """

    def setUp(self):
        """Clear the error collector before each new test."""
        error_collector.clear()

    def tearDown(self):
        """Assert there are no remaining errors."""
        self.assertNoIssues()

    def test_return_literal(self):
        """Test returning a single literal."""
        source = "int main() { return 15; }"
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add(il_commands.Return(15))
        expected_code.add(il_commands.Return(0))

        self.assertEqual(il_code, expected_code)

    def test_return_sum(self):
        """Test returning the sum of two literals."""
        source = "int main() { return 10 + 20; }"
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add(il_commands.Add("t1", 10, 20))
        expected_code.add(il_commands.Return("t1"))
        expected_code.add(il_commands.Return(0))

        self.assertEqual(il_code, expected_code)

    def test_return_variable(self):
        """Test returning a variable."""
        source = "int main() { int a; return a; }"
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add(il_commands.Return("a"))
        expected_code.add(il_commands.Return(0))

        self.assertEqual(il_code, expected_code)

    def test_return_variable_sum(self):
        """Test returning the sum of two variables."""
        source = "int main() { int a; int b; return a+b; }"
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add(il_commands.Add("t1", "a", "b"))
        expected_code.add(il_commands.Return("t1"))
        expected_code.add(il_commands.Return(0))

        self.assertEqual(il_code, expected_code)

    def test_return_variable_equal_sum(self):
        """Test returning a variable that the sum of two variables."""
        source = "int main() { int a; int b; int c; c = a + b; return c; }"
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add(il_commands.Add("t1", "a", "b"))
        expected_code.add(il_commands.Set("c", "t1"))
        expected_code.add(il_commands.Return("c"))
        expected_code.add(il_commands.Return(0))

        self.assertEqual(il_code, expected_code)

    def test_return_variable_equal_product(self):
        """Test returning a variable that is the product of two variables."""
        source = "int main() { int a; int b; int c; c = a * b; return c; }"
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add(il_commands.Mult("t1", "a", "b"))
        expected_code.add(il_commands.Set("c", "t1"))
        expected_code.add(il_commands.Return("c"))
        expected_code.add(il_commands.Return(0))

        self.assertEqual(il_code, expected_code)

    def test_equal_return_value(self):
        """Test that 'a = b' returns the value of 'a'."""
        source = """
                 int main() {
                     int a; int b; int c;
                     c = a = b;
                     return c;
                 }"""
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add(il_commands.Set("a", "b"))
        expected_code.add(il_commands.Set("c", "a"))
        expected_code.add(il_commands.Return("c"))
        expected_code.add(il_commands.Return(0))

        self.assertEqual(il_code, expected_code)

    def test_complex_expression(self):
        """Test a single complex expression."""
        source = """
                 int main() {
                     int a; int b; int c;
                     c = (a * b) + (c + a) * a;
                    return c;
                 }"""
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add(il_commands.Mult("t1", "a", "b"))
        expected_code.add(il_commands.Add("t2", "c", "a"))
        expected_code.add(il_commands.Mult("t3", "t2", "a"))
        expected_code.add(il_commands.Add("t4", "t1", "t3"))
        expected_code.add(il_commands.Set("c", "t4"))
        expected_code.add(il_commands.Return("c"))
        expected_code.add(il_commands.Return(0))

        self.assertEqual(il_code, expected_code)

    def test_error_unassignable(self):
        """Verify errors when expression on left of '=' is unassignable."""
        source = """
                 int main() {
                     3 = 4;
                 }"""
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add(il_commands.Return(0))

        issues = ["error: expression on left of '=' is not assignable"]
        self.assertIssues(issues)
        self.assertEqual(il_code, expected_code)

    def test_error_two_unassignable(self):
        """Verify errors when multiple expressions are unassignable."""
        source = """
                 int main() {
                     int a;
                     3 = 4;
                     a = (5 = 6);
                     a = 10;
                 }"""
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add(il_commands.Set("a", 10))
        expected_code.add(il_commands.Return(0))

        issues = ["error: expression on left of '=' is not assignable",
                  "error: expression on left of '=' is not assignable"]
        self.assertIssues(issues)
        self.assertEqual(il_code, expected_code)

    def test_if_statement(self):
        """Test basic if-statement."""
        source = """
                 int main() {
                     int a;
                     a = 0;
                     if(2) {
                          a = 5;
                     }
                     return a;
                 }
        """
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add(il_commands.Set("a", 0))
        expected_code.add(il_commands.JumpZero("2", 1))
        expected_code.add(il_commands.Set("a", 5))
        expected_code.add(il_commands.Label(1))
        expected_code.add(il_commands.Return("a"))
        expected_code.add(il_commands.Return(0))

        self.assertEqual(il_code, expected_code)

    def test_compound_if_statement(self):
        """Test compound if-statement."""
        source = """
                 int main() {
                     int a;
                     a = 0;
                     if(2) {
                          a = 5;
                          if(3) {
                               a = 10;
                          }
                          a = 7;
                     }
                     return a;
                 }
        """
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add(il_commands.Set("a", 0))
        expected_code.add(il_commands.JumpZero("2", 1))
        expected_code.add(il_commands.Set("a", 5))
        expected_code.add(il_commands.JumpZero("3", 2))
        expected_code.add(il_commands.Set("a", 10))
        expected_code.add(il_commands.Label(2))
        expected_code.add(il_commands.Set("a", 7))
        expected_code.add(il_commands.Label(1))
        expected_code.add(il_commands.Return("a"))
        expected_code.add(il_commands.Return(0))

        self.assertEqual(il_code, expected_code)

    def test_error_in_if_statement(self):
        """Test errors in if-statement are proprerly reported."""
        source = """
                 int main() {
                     int a;
                     a = 0;
                     if(2) 3 = 5;
                     4 = 5;
                     return a;
                 }
        """
        self.make_il_code(source)
        issues = ["error: expression on left of '=' is not assignable",
                  "error: expression on left of '=' is not assignable"]
        self.assertIssues(issues)

    def test_undeclared_identifier(self):
        """Test undeclared identifier raises error."""
        source = """
                 int main() {
                     int a; int b;
                     c = 0;
                     a = d;
                     return e;
                 }
        """
        self.make_il_code(source)
        issues = ["error: use of undeclared identifier 'c'",
                  "error: use of undeclared identifier 'd'",
                  "error: use of undeclared identifier 'e'"]
        self.assertIssues(issues)

    def test_cast_for_math(self):
        """Test chars are converted to ints before math."""
        source = """
                 int main() {
                     char a; char b; a = 10; b = 20;
                     return a + b;
                 }
        """
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add(il_commands.Set("a_char", 10))
        expected_code.add(il_commands.Set("a", "a_char"))
        expected_code.add(il_commands.Set("b_char", 20))
        expected_code.add(il_commands.Set("b", "b_char"))
        expected_code.add(il_commands.Set("a_int", "a"))
        expected_code.add(il_commands.Set("b_int", "b"))
        expected_code.add(il_commands.Add("sum", "a_int", "b_int"))
        expected_code.add(il_commands.Return("sum"))
        expected_code.add(il_commands.Return(0))

        self.assertEqual(il_code, expected_code)

    def make_il_code(self, source):
        """Make IL code from the given source.

        returns (ILCode) - the produced IL code object

        """
        token_list = Lexer().tokenize([(source, "test.c", "7")])

        ast_root = Parser(token_list).parse()

        il_code = ILCode()
        symbol_table = SymbolTable()
        ast_root.make_code(il_code, symbol_table)
        return il_code

if __name__ == "__main__":
    unittest.main()
