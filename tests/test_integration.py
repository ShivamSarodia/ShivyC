"""Integration tests for the compiler. Tests the entire pipeline, from
C source to executable.

The tests in IntegrationTests should focus on verifying that the generated asm
code behaves as expected, and the tests in ErrorTests should focus on verifying
that the correct code generation errors are raised.

If the main test point of a test is to verify the lexer/parser steps, put the
test in test_lexer.py or test_parser.py.

"""

import subprocess
import unittest

from errors import CompilerError
import shivyc

class TestUtil:
    """Contains useful functions for the tests below"""
    def compile_and_run(self, code):
        """Compile, assemble, link, and run the provided C code. Raises an
        exception if any of these steps fails; otherwise, returns the return
        code of the executed program.

        """
        asm_code = shivyc.compile_code([(code, "file_name.c", 7)])
        with open("tests/temp/out.s", "w") as asm_file:
            asm_file.write(asm_code)
        shivyc.assemble_and_link("tests/temp/out", "tests/temp/out.s",
                                 "tests/temp/temp.o")
        return subprocess.run(["tests/temp/out"]).returncode

    def expect_return(self, code, value):
        self.assertEqual(self.compile_and_run(code), value)

    def expect_error(self, code, regex):
        with self.assertRaisesRegex(CompilerError, regex):
            self.compile_and_run(code)

class IntegrationTests(unittest.TestCase, TestUtil):
    def test_basic_return_main(self):
        self.expect_return("int main() { return 15; }", 15)
            
    def test_multiple_return_main(self):
        self.expect_return("int main() { return 15; return 20; return 10; }", 15)

    def test_sum_integers(self):
        self.expect_return("int main() { return 15 + 10 + 5; }", 30)

    def test_product_integers(self):
        self.expect_return("int main() { return 5 * 2 * 3; }", 30)

    def test_parens_integers(self):
        self.expect_return("int main() { return (5 + 3) * 2; }", 16)

    def test_declaration_integer(self):
        self.expect_return("int main() { int a; return 15; }", 15)

    def test_equals_and_return(self):
        self.expect_return("int main() { int a; a = 10; return a; }", 10)

    def test_equals_value(self):
        self.expect_return("int main() { int a; a = 10; return a = 20; }", 20)

    def test_multiple_declarations_and_return(self):
        self.expect_return(
            """int main() {
                    int a; int b; int c; int d;
                    a = 10; b = 20;
                    return a;
             }""", 10)

    def test_add_variable_to_const(self):
        self.expect_return("int main() { int a; a = 10; return a+1; }", 11)

    def test_add_const_to_variable(self):
        self.expect_return("int main() { int a; a = 10; return 1+a; }", 11)

    def test_add_two_variables(self):
        code = "int main() { int a; int b; a = 10; b = 1; return a+b; }"
        self.expect_return(code, 11)

    def test_add_two_variables(self):
        code = "int main() { int a; int b; a = 10; b = 1; return a+b; }"
        self.expect_return(code, 11)

    def test_add_three_variables(self):
        code = """int main() { int a; int b; int c; a = 10; b = 1; c = 3;
                               return a+b+c; }"""
        self.expect_return(code, 14)

    def test_add_two_variables_and_const(self):
        code = "int main() { int a; int b; a = 10; b = 1; return a+b+3; }"
        self.expect_return(code, 14)

    def test_equals_stack(self):
        code = "int main() { int a; int b; a = 10; b = a; return b; }"
        self.expect_return(code, 10)

    def test_equals_register(self):
        code = "int main() { int a; int b; a = 10; b = a + 1; return b; }"
        self.expect_return(code, 11)

    def test_equals_sum_of_self(self):
        code = """int main() { int a; int b; a = 10; b = a + 1;
                               a = a + b; return a; }"""
        self.expect_return(code, 21)

    def test_parens_equals(self):
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
    def test_redeclaration(self):
        self.expect_error("int main() { int var; int var; return 10; }",
                          "redeclaration of 'var'")
    def test_undeclared_return(self):
        self.expect_error("int main() { return var; }",
                          "undeclared identifier 'var'")
    def test_undeclared_equals(self):
        self.expect_error("int main() { a = 10; return a; }",
                          "undeclared identifier 'a'")
