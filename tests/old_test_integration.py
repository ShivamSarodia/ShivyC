"""Old integration tests for the compiler.

Since introducing the IL, most of these no longer pass or test particularly
error-prone parts of the compiler. Tests the entire pipeline, from C source to
executable. The tests in IntegrationTests should focus on verifying that the
generated ASM code behaves as expected, and the tests in ErrorTests should
focus on verifying that the correct code generation errors are raised. If the
main test point of a test is to verify the lexer/parser/IL generation steps,
put the test in the appropriate test_*.py file.

"""

import subprocess
import unittest

import shivyc
from errors import CompilerError


class TestUtil:
    """Useful functions for the integration tests."""

    def compile_and_run(self, code):
        """Compile, assemble, link, and run the provided C code.

        This function raises an exception if any of these steps fails;
        otherwise, it returns the return code of the executed program.

        """
        asm_code = shivyc.compile_code([(code, "file_name.c", 7)])
        with open("tests/temp/out.s", "w") as asm_file:
            asm_file.write(asm_code)
        shivyc.assemble_and_link("tests/temp/out", "tests/temp/out.s",
                                 "tests/temp/temp.o")
        return subprocess.run(["tests/temp/out"]).returncode

    def expect_return(self, code, value):
        """Expect the provided code to return value when compiled.

        code (str) - Code to compile.
        value (int) - Value expected to be returned

        """
        self.assertEqual(self.compile_and_run(code), value)

    def expect_error(self, code, regex):
        """Expect an error when `code` is compiled.

        code (str) - Code to compile.
        regex (str) - Regex that the error message should match

        """
        with self.assertRaisesRegex(CompilerError, regex):
            self.compile_and_run(code)


class IntegrationTests(unittest.TestCase, TestUtil):
    """Tests that are expected to succeed in compiling."""

    def test_basic_return_main(self):
        """Test returning single literal."""
        self.expect_return("int main() { return 15; }", 15)

    def test_multiple_return_main(self):
        """Test multiple return statements."""
        self.expect_return("int main() { return 15; return 20; return 10; }",
                           15)

    def test_sum_integers(self):
        """Test returning sum of literals."""
        self.expect_return("int main() { return 15 + 10 + 5; }", 30)

    def test_product_integers(self):
        """Test returning product of literals."""
        self.expect_return("int main() { return 5 * 2 * 3; }", 30)

    def test_parens_integers(self):
        """Test returning expression of literals."""
        self.expect_return("int main() { return (5 + 3) * 2; }", 16)

    def test_declaration_integer(self):
        """Test returning literal after declaration."""
        self.expect_return("int main() { int a; return 15; }", 15)

    def test_equals_and_return(self):
        """Test returning variable value."""
        self.expect_return("int main() { int a; a = 10; return a; }", 10)

    def test_equals_value(self):
        """Test returning equal expression result."""
        self.expect_return("int main() { int a; a = 10; return a = 20; }", 20)

    def test_multiple_declarations_and_return(self):
        """Test returning variable with extra declarations."""
        self.expect_return("""int main() {
                    int a; int b; int c; int d;
                    a = 10; b = 20;
                    return a;
             }""", 10)

    def test_add_variable_to_const(self):
        """Test returning sum of variable and literal."""
        self.expect_return("int main() { int a; a = 10; return a+1; }", 11)

    def test_add_const_to_variable(self):
        """Test returning sum of literal and variable."""
        self.expect_return("int main() { int a; a = 10; return 1+a; }", 11)

    def test_add_two_variables(self):
        """Test returning sum of variables."""
        code = "int main() { int a; int b; a = 10; b = 1; return a+b; }"
        self.expect_return(code, 11)

    def test_add_three_variables(self):
        """Test returning sum of three variables."""
        code = """int main() { int a; int b; int c; a = 10; b = 1; c = 3;
                               return a+b+c; }"""
        self.expect_return(code, 14)

    def test_add_two_variables_and_const(self):
        """Test returning sum of two variables and literal."""
        code = "int main() { int a; int b; a = 10; b = 1; return a+b+3; }"
        self.expect_return(code, 14)

    def test_equals_stack(self):
        """Test returning variable set to another variable."""
        code = "int main() { int a; int b; a = 10; b = a; return b; }"
        self.expect_return(code, 10)

    def test_equals_register(self):
        """Test returning variable set to sum of variable and literal."""
        code = "int main() { int a; int b; a = 10; b = a + 1; return b; }"
        self.expect_return(code, 11)

    def test_equals_sum_of_self(self):
        """Test returning variable set to sum of self and another variable."""
        code = """int main() { int a; int b; a = 10; b = a + 1;
                               a = a + b; return a; }"""
        self.expect_return(code, 21)

    def test_parens_equals(self):
        """Test returning value from an expression with parentheses."""
        code = """
        int main() {
            int a; int b; int c; int d;
            a = 10; b = 5; c = 15; d = 20;
            d = (a = (c + b)) + d;
            a = d + a;
            return 2 + a;
        }
        """
        self.expect_return(code, 62)


class ErrorTests(unittest.TestCase, TestUtil):
    """Tests that are expected to raise a compiler error."""

    # TODO: All of these can be moved to il_gen.py.
    def test_redeclaration(self):
        """Test error on redeclaration of a variable."""
        self.expect_error("int main() { int var; int var; return 10; }",
                          "redeclaration of 'var'")

    def test_undeclared_return(self):
        """Test error on returning an undeclared variable."""
        self.expect_error("int main() { return var; }",
                          "undeclared identifier 'var'")

    def test_undeclared_equals(self):
        """Test error on setting an undeclared variable."""
        self.expect_error("int main() { a = 10; return a; }",
                          "undeclared identifier 'a'")
