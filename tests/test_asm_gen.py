"""Tests for the IL->ASM phase of the compiler."""

import unittest

import ctypes
from asm_gen import ASMCode
from asm_gen import ASMGen
from il_gen import ILCode
from il_gen import LiteralILValue
from il_gen import TempILValue
from il_gen import VariableILValue


class ASTGenTests(unittest.TestCase):
    """Tests for the IL->ASM phase of the compiler."""

    def test_return_literal(self):
        """Test returning a single literal."""
        il_return_value = LiteralILValue(ctypes.integer, "15")
        il_code = ILCode()
        il_code.add_command(ILCode.RETURN, il_return_value)

        asm_code = ASMCode()
        asm_gen = ASMGen(il_code, asm_code)
        asm_gen.make_asm()

        expected_asm = ["global main", "", "main:", "     mov eax, 15",
                        "     ret"]

        self.assertEqual(asm_code.full_code(), '\n'.join(expected_asm))

    def test_return_uninit_variable(self):
        """Test returning an uninitialized variable."""
        il_return_variable = VariableILValue(ctypes.integer, 4)
        il_code = ILCode()
        il_code.add_command(ILCode.RETURN, il_return_variable)

        asm_code = ASMCode()
        asm_gen = ASMGen(il_code, asm_code)
        asm_gen.make_asm()

        expected_asm = ["global main", "", "main:",
                        "     mov eax, DWORD [rbp-4]", "     ret"]

        self.assertEqual(asm_code.full_code(), '\n'.join(expected_asm))

    def test_return_init_variable(self):
        """Test returning an initialized variable."""
        il_return_literal = LiteralILValue(ctypes.integer, "15")
        il_return_variable = VariableILValue(ctypes.integer, 4)
        il_code = ILCode()
        il_code.add_command(ILCode.SET, il_return_literal, None,
                            il_return_variable)
        il_code.add_command(ILCode.RETURN, il_return_variable)

        asm_code = ASMCode()
        asm_gen = ASMGen(il_code, asm_code)
        asm_gen.make_asm()

        expected_asm = ["global main", "", "main:", "     mov eax, 15",
                        "     ret"]

        self.assertEqual(asm_code.full_code(), '\n'.join(expected_asm))

    def test_return_uninit_variable_chain(self):
        """Test returning from a long uninitialized variable chain."""
        il_return_variable1 = VariableILValue(ctypes.integer, 4)
        il_return_variable2 = VariableILValue(ctypes.integer, 8)
        il_return_variable3 = VariableILValue(ctypes.integer, 12)
        il_return_variable4 = VariableILValue(ctypes.integer, 16)
        il_return_variable5 = VariableILValue(ctypes.integer, 20)
        il_code = ILCode()
        il_code.add_command(ILCode.SET, il_return_variable1, None,
                            il_return_variable2)
        il_code.add_command(ILCode.SET, il_return_variable2, None,
                            il_return_variable3)
        il_code.add_command(ILCode.SET, il_return_variable3, None,
                            il_return_variable4)
        il_code.add_command(ILCode.SET, il_return_variable4, None,
                            il_return_variable5)
        il_code.add_command(ILCode.RETURN, il_return_variable5)

        asm_code = ASMCode()
        asm_gen = ASMGen(il_code, asm_code)
        asm_gen.make_asm()

        expected_asm = ["global main", "", "main:",
                        "     mov eax, DWORD [rbp-4]", "     ret"]

        self.assertEqual(asm_code.full_code(), '\n'.join(expected_asm))

    def test_return_init_variable_chain(self):
        """Test returning from a long initialized variable chain."""
        il_return_literal = LiteralILValue(ctypes.integer, "15")
        il_return_variable1 = VariableILValue(ctypes.integer, 4)
        il_return_variable2 = VariableILValue(ctypes.integer, 8)
        il_return_variable3 = VariableILValue(ctypes.integer, 12)
        il_return_variable4 = VariableILValue(ctypes.integer, 16)
        il_return_variable5 = VariableILValue(ctypes.integer, 20)
        il_code = ILCode()
        il_code.add_command(ILCode.SET, il_return_literal, None,
                            il_return_variable1)
        il_code.add_command(ILCode.SET, il_return_variable1, None,
                            il_return_variable2)
        il_code.add_command(ILCode.SET, il_return_variable2, None,
                            il_return_variable3)
        il_code.add_command(ILCode.SET, il_return_variable3, None,
                            il_return_variable4)
        il_code.add_command(ILCode.SET, il_return_variable4, None,
                            il_return_variable5)
        il_code.add_command(ILCode.RETURN, il_return_variable5)

        asm_code = ASMCode()
        asm_gen = ASMGen(il_code, asm_code)
        asm_gen.make_asm()

        expected_asm = ["global main", "", "main:", "     mov eax, 15",
                        "     ret"]

        self.assertEqual(asm_code.full_code(), '\n'.join(expected_asm))

    def test_literal_int_addition(self):
        """Test literal integer addition."""
        il_literal_1 = LiteralILValue(ctypes.integer, "15")
        il_literal_2 = LiteralILValue(ctypes.integer, "20")
        il_temp_1 = TempILValue(ctypes.integer)
        il_code = ILCode()
        il_code.add_command(ILCode.ADD, il_literal_1, il_literal_2, il_temp_1)
        il_code.add_command(ILCode.RETURN, il_temp_1)

        asm_code = ASMCode()
        ASMGen(il_code, asm_code).make_asm()

        expected_asm = ["global main", "", "main:", "     mov eax, 35",
                        "     ret"]

        self.assertEqual(asm_code.full_code(), '\n'.join(expected_asm))

    def test_literal_multiple_int_addition(self):
        """Test multiple literal integer addition."""
        il_literal_1 = LiteralILValue(ctypes.integer, "15")
        il_literal_2 = LiteralILValue(ctypes.integer, "20")
        il_literal_3 = LiteralILValue(ctypes.integer, "25")
        il_literal_4 = LiteralILValue(ctypes.integer, "30")
        il_literal_5 = LiteralILValue(ctypes.integer, "25")
        il_literal_6 = LiteralILValue(ctypes.integer, "20")
        il_temp_1 = TempILValue(ctypes.integer)
        il_temp_2 = TempILValue(ctypes.integer)
        il_temp_3 = TempILValue(ctypes.integer)
        il_temp_4 = TempILValue(ctypes.integer)
        il_temp_5 = TempILValue(ctypes.integer)
        il_code = ILCode()
        il_code.add_command(ILCode.ADD, il_literal_1, il_literal_2, il_temp_1)
        il_code.add_command(ILCode.ADD, il_literal_3, il_literal_4, il_temp_2)
        il_code.add_command(ILCode.ADD, il_temp_2, il_literal_5, il_temp_3)
        il_code.add_command(ILCode.ADD, il_temp_3, il_temp_1, il_temp_4)
        il_code.add_command(ILCode.ADD, il_temp_4, il_literal_6, il_temp_5)
        il_code.add_command(ILCode.RETURN, il_temp_5)

        asm_code = ASMCode()
        ASMGen(il_code, asm_code).make_asm()

        expected_asm = ["global main", "", "main:", "     mov eax, 135",
                        "     ret"]

        self.assertEqual(asm_code.full_code(), '\n'.join(expected_asm))

    def test_add_literal_to_itself(self):
        """Test adding literal to itself."""
        il_literal_1 = LiteralILValue(ctypes.integer, "15")
        il_literal_2 = LiteralILValue(ctypes.integer, "15")
        il_temp_1 = TempILValue(ctypes.integer)
        il_code = ILCode()
        il_code.add_command(ILCode.ADD, il_literal_1, il_literal_2, il_temp_1)
        il_code.add_command(ILCode.RETURN, il_temp_1)

        asm_code = ASMCode()
        ASMGen(il_code, asm_code).make_asm()

        expected_asm = ["global main", "", "main:", "     mov eax, 30",
                        "     ret"]

        self.assertEqual(asm_code.full_code(), '\n'.join(expected_asm))

    def test_add_stack_values(self):
        """Test adding two stack values."""
        il_variable_1 = VariableILValue(ctypes.integer, 4)
        il_variable_2 = VariableILValue(ctypes.integer, 8)
        il_temp_1 = TempILValue(ctypes.integer)
        il_code = ILCode()
        il_code.add_command(ILCode.ADD, il_variable_1, il_variable_2,
                            il_temp_1)
        il_code.add_command(ILCode.RETURN, il_temp_1)

        asm_code = ASMCode()
        ASMGen(il_code, asm_code).make_asm()

        expected_asm = ["global main", "", "main:",
                        "     mov eax, DWORD [rbp-4]",
                        "     add eax, DWORD [rbp-8]", "     ret"]

        self.assertEqual(asm_code.full_code(), '\n'.join(expected_asm))

    def test_add_stack_values_to_variable(self):
        """Test adding two stack values."""
        il_variable_1 = VariableILValue(ctypes.integer, 4)
        il_variable_2 = VariableILValue(ctypes.integer, 8)
        il_variable_3 = VariableILValue(ctypes.integer, 12)
        il_code = ILCode()
        il_code.add_command(ILCode.ADD, il_variable_1, il_variable_2,
                            il_variable_3)
        il_code.add_command(ILCode.RETURN, il_variable_3)

        asm_code = ASMCode()
        ASMGen(il_code, asm_code).make_asm()

        expected_asm = ["global main", "", "main:",
                        "     mov eax, DWORD [rbp-4]",
                        "     add eax, DWORD [rbp-8]", "     ret"]

        self.assertEqual(asm_code.full_code(), '\n'.join(expected_asm))

    def test_add_equals_value(self):
        """Test: b = (c = a) + b."""
        il_variable_1 = VariableILValue(ctypes.integer, 4)
        il_variable_2 = VariableILValue(ctypes.integer, 8)
        il_variable_3 = VariableILValue(ctypes.integer, 12)
        il_temp_1 = TempILValue(ctypes.integer)
        il_code = ILCode()
        il_code.add_command(ILCode.SET, il_variable_1, None, il_variable_3)
        il_code.add_command(ILCode.ADD, il_variable_3, il_variable_2,
                            il_temp_1)
        il_code.add_command(ILCode.SET, il_temp_1, None, il_variable_2)
        il_code.add_command(ILCode.RETURN, il_variable_2)

        asm_code = ASMCode()
        ASMGen(il_code, asm_code).make_asm()

        expected_asm = ["global main", "", "main:",
                        "     mov eax, DWORD [rbp-4]",
                        "     add eax, DWORD [rbp-8]", "     ret"]

        self.assertEqual(asm_code.full_code(), '\n'.join(expected_asm))

    def test_complex_expression(self):
        """Test complex expression: c = a + b + (3 + c) + a."""
        il_variable_1 = VariableILValue(ctypes.integer, 4)
        il_variable_2 = VariableILValue(ctypes.integer, 8)
        il_variable_3 = VariableILValue(ctypes.integer, 12)
        il_literal_1 = LiteralILValue(ctypes.integer, "3")
        il_temp_1 = TempILValue(ctypes.integer)
        il_temp_2 = TempILValue(ctypes.integer)
        il_temp_3 = TempILValue(ctypes.integer)
        il_code = ILCode()
        il_code.add_command(ILCode.ADD, il_variable_1, il_variable_2,
                            il_temp_1)
        il_code.add_command(ILCode.ADD, il_literal_1, il_variable_3, il_temp_2)
        il_code.add_command(ILCode.ADD, il_temp_1, il_temp_2, il_temp_3)
        il_code.add_command(ILCode.ADD, il_temp_3, il_variable_1,
                            il_variable_3)
        il_code.add_command(ILCode.RETURN, il_variable_3)

        asm_code = ASMCode()
        ASMGen(il_code, asm_code).make_asm()

        expected_asm = ["global main", "", "main:",
                        "     mov eax, DWORD [rbp-4]",
                        "     add eax, DWORD [rbp-8]", "     mov esi, 3",
                        "     add esi, DWORD [rbp-12]", "     add eax, esi",
                        "     add eax, DWORD [rbp-4]", "     ret"]

        self.assertEqual(asm_code.full_code(), '\n'.join(expected_asm))

    def test_useless_addition(self):
        """Test a useless addition statement.

        We expect that code will not be generated for the useless
        addition statement.

        """
        il_variable_1 = VariableILValue(ctypes.integer, 4)
        il_variable_2 = VariableILValue(ctypes.integer, 8)
        il_variable_3 = VariableILValue(ctypes.integer, 12)
        il_temp_1 = TempILValue(ctypes.integer)
        il_temp_2 = TempILValue(ctypes.integer)
        il_code = ILCode()
        il_code.add_command(ILCode.ADD, il_variable_1, il_variable_2,
                            il_temp_1)
        il_code.add_command(ILCode.ADD, il_variable_1, il_variable_3,
                            il_temp_2)
        il_code.add_command(ILCode.RETURN, il_temp_2)

        asm_code = ASMCode()
        ASMGen(il_code, asm_code).make_asm()

        expected_asm = ["global main", "", "main:",
                        "     mov eax, DWORD [rbp-4]",
                        "     add eax, DWORD [rbp-12]", "     ret"]

        self.assertEqual(asm_code.full_code(), '\n'.join(expected_asm))
