"""Integration tests for the compiler. Tests the entire pipeline, from
C source to executable"""

import subprocess
import unittest

from errors import CompilerError
import shivyc

class integration_tests(unittest.TestCase):
    def setUp(self):
        pass
    
    def test_basic_return_main(self):
        self.expect_return("int main() { return 15; }", 15)

    # Currently fails! Reminder to fix this bug.
    def test_extra_tokens_at_end(self):
        self.expect_exception("int main() { return 15; } int",
                              CompilerError, "unexpected token")
        
    # Support functions for the the tests
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

    def expect_exception(self, code, exception, regex):
        with self.assertRaisesRegex(exception, regex):
            self.compile_and_run(code)
