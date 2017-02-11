"""Integration tests for the compiler.

Tests the entire pipeline, from C source to executable. These tests should
focus on verifying that the generated ASM code behaves as expected. Ideally,
for every feature tested here (except stress tests), we'll also have tests in
one or more of the other test_*.py files.

"""

import subprocess
import unittest
import shivyc

from asm_gen import ASMCode, ASMGen
from errors import error_collector
from il_gen import ILCode, SymbolTable
from lexer import Lexer
from parser import Parser


class IntegrationTestUtil(unittest.TestCase):
    """Useful functions for the integration tests."""

    def compile_and_run(self, code):
        """Compile, assemble, link, and run the provided C code.

        This function raises an exception if any of these steps fails.
        Otherwise, it returns the return code of the compiled program.

        """
        token_list = Lexer().tokenize([(code, "test.c", 7)])
        ast_root = Parser(token_list).parse()
        il_code = ILCode()
        ast_root.make_code(il_code, SymbolTable())
        asm_code = ASMCode()
        ASMGen(il_code, asm_code).make_asm()
        asm_source = asm_code.full_code()

        asm_filename = "tests/temp/out.s"
        shivyc.write_asm(asm_source, asm_filename)
        shivyc.assemble_and_link("tests/temp/out", "tests/temp/out.s",
                                 "tests/temp/temp.o")
        ret = subprocess.call(["tests/temp/out"])

        self.assertTrue(error_collector.ok())
        return ret

    def assertReturns(self, code, value):
        """Assert that the code returns the given value."""
        self.assertEqual(self.compile_and_run(code), value)


class IntegrationTests(IntegrationTestUtil):
    """Integration tests for the compiler."""

    def test_basic_return_main(self):
        """Test returning single literal."""
        self.assertReturns("int main() { return 15; }", 15)

    def test_chain_equals(self):
        """Test a long, complex chain of equality."""
        source = """
        int main() {
            int a; int b; int c; int d; int e; int f; int g; int h;
            a = b = 10;
            b = c;
            c = d;
            d = e;
            e = 20;
            f = e;
            g = h = f;
            return g;
        }
        """
        self.assertReturns(source, 20)

    def test_simple_addition(self):
        """Test a simple addition of variables."""
        source = """
        int main() {
            int a; int b;
            a = 5; b = 10;
            return a + b;
        }
        """
        self.assertReturns(source, 15)

    def test_complex_addition(self):
        """Test complex addition of variables."""
        source = """
        int main() {
            int a; int b; int c; int d;
            a = 5; b = 10;
            c = a + b + (a + b);
            d = c + c + 3;
            return d;
        }
        """
        self.assertReturns(source, 63)

    def test_simple_multiplcation(self):
        """Test simple multiplication of variables."""
        source = """
        int main() {
            int a; int b;
            a = 5; b = 10;
            return a * b;
        }
        """
        self.assertReturns(source, 50)

    def test_complex_math(self):
        """Test complex multiplication of variables."""
        source = """
        int main() {
            int a; int b; int c; int d;
            a = 5; b = 10;
            c = b + a * b + 10 * a + 10 * 3;
            d = c * b + a;
            return d * c;
        }
        """

        a = 5
        b = 10
        c = b + a * b + 10 * a + 10 * 3
        d = c * b + a
        final = d * c

        self.assertReturns(source, final % 256)
