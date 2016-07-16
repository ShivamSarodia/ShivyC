"""Implements tests for the code generation phase of the compiler

"""
import unittest

import ast
from code_gen import CodeStore
from tokens import Token
import token_kinds

class code_gen_tests(unittest.TestCase):
    def setUp(self):
        pass

    def test_asm_output(self):
        main_node = ast.MainNode(Token(token_kinds.number, "15"))

        code_store = CodeStore()
        main_node.make_code(code_store)

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
                         "     ret"]

        self.assertEqual(code_store.full_code(),
                         "\n".join(expected_code))


if __name__ == "__main__":
    unittest.main()
