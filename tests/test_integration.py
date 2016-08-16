"""Integration tests for the compiler.

Tests the entire pipeline, from C source to executable. These tests should
focus on verifying that the generated ASM code behaves as expected. Ideally,
for every feature tested here (except stress tests), we'll also have tests in
one or more of the other test_*.py files.

"""

import subprocess
import unittest

import token_kinds
from lexer import Lexer
from parser import Parser
from il_gen import ILCode
from il_gen import SymbolTable
from asm_gen import ASMCode
from asm_gen import ASMGen
from shivyc import assemble_and_link


class TestUtil(unittest.TestCase):
    """Useful functions for the integration tests."""

    def compile_and_run(self, code):
        """Compile, assemble, link, and run the provided C code.

        This function raises an exception if any of these steps fails.
        Otherwise, it returns the return code of the compiled program.

        """
        lexer = Lexer(token_kinds.symbol_kinds, token_kinds.keyword_kinds)
        token_list = lexer.tokenize([(code, "filename.c", 7)])

        ast_root = Parser(token_list).parse()

        il_code = ILCode()
        symbol_table = SymbolTable()
        ast_root.make_code(il_code, symbol_table)

        asm_code = ASMCode()
        ASMGen(il_code, asm_code).make_asm()

        s_source = asm_code.full_code()
        with open("tests/temp/out.s", "w") as s_file:
            s_file.write(s_source)
        assemble_and_link("tests/temp/out", "tests/temp/out.s",
                          "tests/temp/temp.o")
        return subprocess.call(["tests/temp/out"])

    def assertReturns(self, code, value):
        """Assert that the code returns the given value."""
        self.assertEqual(self.compile_and_run(code), value)


class IntegrationTests(TestUtil):
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
