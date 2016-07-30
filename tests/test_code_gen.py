"""Implements tests for the code generation phase of the compiler

"""
import unittest

import ast
from code_gen import CodeStore
from code_gen import SymbolState
from tokens import Token
import token_kinds

class code_gen_tests(unittest.TestCase):
    def setUp(self):
        pass

    def test_asm_output(self):
        main_node = ast.MainNode(
            [ast.ReturnNode(
                ast.NumberNode(Token(token_kinds.number, "15")))])
        
        code_store = CodeStore()
        symbol_state = SymbolState()
        main_node.make_code(code_store, symbol_state)

        expected_code = ["global _start",
                         "",
                         "_start:",
                         "     call main",
                         "     mov rdi, rax",
                         "     mov rax, 60",
                         "     syscall",
                         "main:",
                         "     push rbp",
                         "     mov rbp, rsp",
                         "     mov rax, 15",
                         "     pop rbp",
                         "     ret",
                         "     mov rax, 0",
                         "     pop rbp",
                         "     ret"]

        self.assertEqual(code_store.full_code(),
                         "\n".join(expected_code))

    def test_empty_asm_output(self):
        main_node = ast.MainNode([])

        code_store = CodeStore()
        symbol_state = SymbolState()
        main_node.make_code(code_store, symbol_state)

        expected_code = ["global _start",
                         "",
                         "_start:",
                         "     call main",
                         "     mov rdi, rax",
                         "     mov rax, 60",
                         "     syscall",
                         "main:",
                         "     push rbp",
                         "     mov rbp, rsp",
                         "     mov rax, 0",
                         "     pop rbp",
                         "     ret"]

        self.assertEqual(code_store.full_code(),
                         "\n".join(expected_code))

    def test_rsp_shifting(self):
        main_node = ast.MainNode(
            [ast.DeclarationNode(Token(token_kinds.identifier, "var1")),
             ast.DeclarationNode(Token(token_kinds.identifier, "var2")),
             ast.DeclarationNode(Token(token_kinds.identifier, "var3")),
             ast.DeclarationNode(Token(token_kinds.identifier, "var4")),
             ast.DeclarationNode(Token(token_kinds.identifier, "var5")),
             ast.DeclarationNode(Token(token_kinds.identifier, "var6")),
             ast.DeclarationNode(Token(token_kinds.identifier, "var7")),
             ast.DeclarationNode(Token(token_kinds.identifier, "var8")),
             ast.DeclarationNode(Token(token_kinds.identifier, "var9")),
             ast.DeclarationNode(Token(token_kinds.identifier, "var10")),
             ast.ReturnNode(
                 ast.NumberNode(Token(token_kinds.number, "15")))])
        
        code_store = CodeStore()
        symbol_state = SymbolState()
        main_node.make_code(code_store, symbol_state)

        expected_code = ["global _start",
                         "",
                         "_start:",
                         "     call main",
                         "     mov rdi, rax",
                         "     mov rax, 60",
                         "     syscall",
                         "main:",
                         "     push rbp",
                         "     mov rbp, rsp",
                         "     sub rsp, 48",
                         "     mov rax, 15",
                         "     add rsp, 48",
                         "     pop rbp",
                         "     ret",
                         "     mov rax, 0",
                         "     add rsp, 48",
                         "     pop rbp",
                         "     ret"]

        self.assertEqual(code_store.full_code(),
                         "\n".join(expected_code))

if __name__ == "__main__":
    unittest.main()
