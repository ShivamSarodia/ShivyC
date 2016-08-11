import unittest

import ast
import token_kinds
from il_gen import ILCode
from il_gen import SymbolTable
from lexer import Lexer
from parser import Parser
from tokens import Token

class ILGenTests(unittest.TestCase):
    """Tests the AST->IL phase of the compiler.

    We're lowkey cheating here--these are more of integration tests than unit
    tests, because we're also tokenizing/parsing the input string. However,
    writing out the parsed form for every test is a lot of struggle that's not
    really worth it given that we have good tests of the parsing phase
    anyway.
    """
    
    def test_return_literal(self):
        source = "int main() { return 15; }"
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add_command(ILCode.RETURN, 15)
        expected_code.add_command(ILCode.RETURN, 0)

        self.assertEqual(il_code, expected_code)
            
    def test_return_sum(self):
        source = "int main() { return 10 + 20; }"
        il_code = self.make_il_code(source)
        
        expected_code = ILCode()
        expected_code.add_command(ILCode.ADD, 10, 20, "t1")
        expected_code.add_command(ILCode.RETURN, "t1")
        expected_code.add_command(ILCode.RETURN, 0)

        self.assertEqual(il_code, expected_code)

    def test_return_variable(self):
        source = "int main() { int a; return a; }"
        il_code = self.make_il_code(source)
        
        expected_code = ILCode()
        expected_code.add_command(ILCode.RETURN, "a")
        expected_code.add_command(ILCode.RETURN, 0)

        self.assertEqual(il_code, expected_code)

    def test_return_variable_sum(self):
        source = "int main() { int a; int b; return a+b; }"
        il_code = self.make_il_code(source)
            
        expected_code = ILCode()
        expected_code.add_command(ILCode.ADD, "a", "b", "t1")
        expected_code.add_command(ILCode.RETURN, "t1")
        expected_code.add_command(ILCode.RETURN, 0)

        self.assertEqual(il_code, expected_code)

    def test_return_variable_equal_sum(self):
        source = "int main() { int a; int b; int c; c = a + b; return c; }"
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add_command(ILCode.ADD, "a", "b", "t1")
        expected_code.add_command(ILCode.SET, "t1", None, "c")
        expected_code.add_command(ILCode.RETURN, "c")
        expected_code.add_command(ILCode.RETURN, 0)

        self.assertEqual(il_code, expected_code)

    def test_return_variable_equal_product(self):
        source = "int main() { int a; int b; int c; c = a * b; return c; }"
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add_command(ILCode.MULT, "a", "b", "t1")
        expected_code.add_command(ILCode.SET, "t1", None, "c")
        expected_code.add_command(ILCode.RETURN, "c")
        expected_code.add_command(ILCode.RETURN, 0)

        self.assertEqual(il_code, expected_code)

    def test_equal_return_value(self):
        source = """
                 int main() {
                     int a; int b; int c;
                     c = a = b;
                     return c; 
                 }"""
        il_code = self.make_il_code(source)
        
        expected_code = ILCode()
        expected_code.add_command(ILCode.SET, "b", None, "a")
        expected_code.add_command(ILCode.SET, "a", None, "c")
        expected_code.add_command(ILCode.RETURN, "c")
        expected_code.add_command(ILCode.RETURN, 0)

        self.assertEqual(il_code, expected_code)
        
    def test_complex_expression(self):
        source = """
                 int main() {
                     int a; int b; int c;
                     c = (a * b) + (c + a) * a;
                    return c;
                 }"""
        il_code = self.make_il_code(source)

        expected_code = ILCode()
        expected_code.add_command(ILCode.MULT, "a", "b", "t1")
        expected_code.add_command(ILCode.ADD, "c", "a", "t2")
        expected_code.add_command(ILCode.MULT, "t2", "a", "t3")
        expected_code.add_command(ILCode.ADD, "t1", "t3", "t4")
        expected_code.add_command(ILCode.SET, "t4", None, "c")
        expected_code.add_command(ILCode.RETURN, "c")
        expected_code.add_command(ILCode.RETURN, 0)

        self.assertEqual(il_code, expected_code)
        
    def make_il_code(self, source):
        """Make IL code from the given source and return the ILCode object.
        """
        lexer = Lexer(token_kinds.symbol_kinds, token_kinds.keyword_kinds)
        token_list = lexer.tokenize([(source, "test.c", "7")])
        
        ast_root = Parser(token_list).parse()
        
        il_code = ILCode()
        symbol_table = SymbolTable()
        ast_root.make_code(il_code, symbol_table)
        return il_code

if __name__ == "__main__":
    unittest.main()
