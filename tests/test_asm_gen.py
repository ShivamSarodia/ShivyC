"""Tests for the IL->ASM phase of the compiler."""

import unittest

import ctypes
import il_commands
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
        il_code.add(il_commands.Return(il_return_value))

        asm_code = ASMCode()
        asm_gen = ASMGen(il_code, asm_code)
        asm_gen.make_asm()

        expected = ASMCode()
        expected.add_command("push", "rbp")
        expected.add_command("mov", "rbp", "rsp")
        expected.add_command("sub", "rsp", "0")
        expected.add_command("mov", "eax", "15")
        expected.add_command("mov", "rsp", "rbp")
        expected.add_command("pop", "rbp")
        expected.add_command("ret")

        self.assertEqual(asm_code.full_code(), expected.full_code())

    def test_return_uninit_variable(self):
        """Test returning an uninitialized variable."""
        il_return_variable = VariableILValue(ctypes.integer, 4)
        il_code = ILCode()
        il_code.add(il_commands.Return(il_return_variable))

        asm_code = ASMCode()
        asm_gen = ASMGen(il_code, asm_code)
        asm_gen.make_asm()

        expected = ASMCode()
        expected.add_command("push", "rbp")
        expected.add_command("mov", "rbp", "rsp")
        expected.add_command("sub", "rsp", "4")
        expected.add_command("mov", "eax", "DWORD [rbp-4]")
        expected.add_command("mov", "rsp", "rbp")
        expected.add_command("pop", "rbp")
        expected.add_command("ret")

        self.assertEqual(asm_code.full_code(), expected.full_code())

    def test_return_init_variable(self):
        """Test returning an initialized variable."""
        il_return_literal = LiteralILValue(ctypes.integer, "15")
        il_return_variable = VariableILValue(ctypes.integer, 4)
        il_code = ILCode()
        il_code.add(il_commands.Set(il_return_variable, il_return_literal))
        il_code.add(il_commands.Return(il_return_variable))

        asm_code = ASMCode()
        asm_gen = ASMGen(il_code, asm_code)
        asm_gen.make_asm()

        expected = ASMCode()
        expected.add_command("push", "rbp")
        expected.add_command("mov", "rbp", "rsp")
        expected.add_command("sub", "rsp", "4")
        expected.add_command("mov", "DWORD [rbp-4]", "15")
        expected.add_command("mov", "eax", "DWORD [rbp-4]")
        expected.add_command("mov", "rsp", "rbp")
        expected.add_command("pop", "rbp")
        expected.add_command("ret")

        self.assertEqual(asm_code.full_code(), expected.full_code())

    def test_return_variable_chain(self):
        """Test returning from a initialized variable chain."""
        il_literal = LiteralILValue(ctypes.integer, "15")
        il_variable1 = VariableILValue(ctypes.integer, 4)
        il_variable2 = VariableILValue(ctypes.integer, 8)
        il_code = ILCode()
        il_code.add(il_commands.Set(il_variable1, il_literal))
        il_code.add(il_commands.Set(il_variable2, il_variable1))
        il_code.add(il_commands.Return(il_variable2))

        asm_code = ASMCode()
        asm_gen = ASMGen(il_code, asm_code)
        asm_gen.make_asm()

        expected = ASMCode()
        expected.add_command("push", "rbp")
        expected.add_command("mov", "rbp", "rsp")
        expected.add_command("sub", "rsp", "8")
        expected.add_command("mov", "DWORD [rbp-4]", "15")
        expected.add_command("mov", "eax", "DWORD [rbp-4]")
        expected.add_command("mov", "DWORD [rbp-8]", "eax")
        expected.add_command("mov", "eax", "DWORD [rbp-8]")
        expected.add_command("mov", "rsp", "rbp")
        expected.add_command("pop", "rbp")
        expected.add_command("ret")

        self.assertEqual(asm_code.full_code(), expected.full_code())

    def test_literal_int_addition(self):
        """Test literal integer addition."""
        il_literal_1 = LiteralILValue(ctypes.integer, "15")
        il_literal_2 = LiteralILValue(ctypes.integer, "20")
        il_temp_1 = TempILValue(ctypes.integer)
        il_code = ILCode()
        il_code.add(il_commands.Add(il_temp_1, il_literal_1, il_literal_2))
        il_code.add(il_commands.Return(il_temp_1))

        asm_code = ASMCode()
        ASMGen(il_code, asm_code).make_asm()

        expected = ASMCode()
        expected.add_command("push", "rbp")
        expected.add_command("mov", "rbp", "rsp")
        expected.add_command("sub", "rsp", "4")
        expected.add_command("mov", "eax", "15")
        expected.add_command("add", "eax", "20")
        expected.add_command("mov", "DWORD [rbp-4]", "eax")
        expected.add_command("mov", "eax", "DWORD [rbp-4]")
        expected.add_command("mov", "rsp", "rbp")
        expected.add_command("pop", "rbp")
        expected.add_command("ret")

        self.assertEqual(asm_code.full_code(), expected.full_code())

    def test_add_stack_values(self):
        """Test adding two stack values."""
        il_variable_1 = VariableILValue(ctypes.integer, 4)
        il_variable_2 = VariableILValue(ctypes.integer, 8)
        il_temp_1 = TempILValue(ctypes.integer)
        il_code = ILCode()
        il_code.add(il_commands.Add(il_temp_1, il_variable_1, il_variable_2))
        il_code.add(il_commands.Return(il_temp_1))

        asm_code = ASMCode()
        ASMGen(il_code, asm_code).make_asm()

        expected = ASMCode()
        expected.add_command("push", "rbp")
        expected.add_command("mov", "rbp", "rsp")
        expected.add_command("sub", "rsp", "12")
        expected.add_command("mov", "eax", "DWORD [rbp-4]")
        expected.add_command("add", "eax", "DWORD [rbp-8]")
        expected.add_command("mov", "DWORD [rbp-12]", "eax")
        expected.add_command("mov", "eax", "DWORD [rbp-12]")
        expected.add_command("mov", "rsp", "rbp")
        expected.add_command("pop", "rbp")
        expected.add_command("ret")

        self.assertEqual(asm_code.full_code(), expected.full_code())

    def test_add_temp_values(self):
        """Test adding two temporary values."""
        il_variable_1 = VariableILValue(ctypes.integer, 4)
        il_variable_2 = VariableILValue(ctypes.integer, 8)
        il_temp_1 = TempILValue(ctypes.integer)
        il_temp_2 = TempILValue(ctypes.integer)
        il_temp_3 = TempILValue(ctypes.integer)
        il_code = ILCode()
        il_code.add(il_commands.Add(il_temp_1, il_variable_1, il_variable_2))
        il_code.add(il_commands.Add(il_temp_2, il_variable_1, il_variable_2))
        il_code.add(il_commands.Add(il_temp_3, il_temp_1, il_temp_2))
        il_code.add(il_commands.Return(il_temp_3))

        asm_code = ASMCode()
        ASMGen(il_code, asm_code).make_asm()

        expected = ASMCode()
        expected.add_command("push", "rbp")
        expected.add_command("mov", "rbp", "rsp")
        expected.add_command("sub", "rsp", "20")
        expected.add_command("mov", "eax", "DWORD [rbp-4]")
        expected.add_command("add", "eax", "DWORD [rbp-8]")
        expected.add_command("mov", "DWORD [rbp-12]", "eax")
        expected.add_command("mov", "eax", "DWORD [rbp-4]")
        expected.add_command("add", "eax", "DWORD [rbp-8]")
        expected.add_command("mov", "DWORD [rbp-16]", "eax")
        expected.add_command("mov", "eax", "DWORD [rbp-12]")
        expected.add_command("add", "eax", "DWORD [rbp-16]")
        expected.add_command("mov", "DWORD [rbp-20]", "eax")
        expected.add_command("mov", "eax", "DWORD [rbp-20]")
        expected.add_command("mov", "rsp", "rbp")
        expected.add_command("pop", "rbp")
        expected.add_command("ret")

        self.assertEqual(asm_code.full_code(), expected.full_code())
