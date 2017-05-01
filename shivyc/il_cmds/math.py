"""IL commands for mathematical operations."""

import shivyc.asm_cmds as asm_cmds
import shivyc.spots as spots
from shivyc.il_cmds.base import ILCommand


class _AddMult(ILCommand):
    """Base class for ADD and MULT.

    Contains function that implements the shared code between these.
    """

    def _shared_asm(self, Inst, comm, out, arg1, arg2, spotmap, get_reg,
                    asm_code):
        """Make the shared ASM for ADD, MULT, and SUB.

        Inst - the instruction for this
        comm (Bool) - whether the instruction is commutative. if not,
        a "neg" instruction is inserted when the order is flipped.
        """
        ctype = arg1.ctype
        size = ctype.size

        arg1_spot = spotmap[arg1]
        arg2_spot = spotmap[arg2]

        # Get temp register for computation.
        temp = get_reg([spotmap[out],
                        arg1_spot,
                        arg2_spot])

        if temp == arg1_spot:
            if not self._is_imm64(arg2_spot):
                asm_code.add(Inst(temp, arg2_spot, size))
            else:
                temp2 = get_reg([], [temp])
                asm_code.add(asm_cmds.Mov(temp2, arg2_spot, size))
                asm_code.add(Inst(temp, temp2, size))
        elif temp == arg2_spot:
            if not self._is_imm64(arg1_spot):
                asm_code.add(Inst(temp, arg1_spot, size))
            else:
                temp2 = get_reg([], [temp])
                asm_code.add(asm_cmds.Mov(temp2, arg1_spot, size))
                asm_code.add(Inst(temp, temp2, size))

            if not comm:
                asm_code.add(asm_cmds.Neg(temp, None, size))

        else:
            if (not self._is_imm64(arg1_spot) and
                 not self._is_imm64(arg2_spot)):
                asm_code.add(asm_cmds.Mov(temp, arg1_spot, size))
                asm_code.add(Inst(temp, arg2_spot, size))
            elif (self._is_imm64(arg1_spot) and
                  not self._is_imm64(arg2_spot)):
                asm_code.add(asm_cmds.Mov(temp, arg1_spot, size))
                asm_code.add(Inst(temp, arg2_spot, size))
            elif (not self._is_imm64(arg1_spot) and
                  self._is_imm64(arg2_spot)):
                asm_code.add(asm_cmds.Mov(temp, arg2_spot, size))
                asm_code.add(Inst(temp, arg1_spot, size))
                if not comm:
                    asm_code.add(asm_cmds.Neg(temp, None, size))

            else:  # both are imm64
                temp2 = get_reg([], [temp])

                asm_code.add(asm_cmds.Mov(temp, arg1_spot, size))
                asm_code.add(asm_cmds.Mov(temp2, arg2_spot, size))
                asm_code.add(Inst(temp, temp2, size))

        if temp != spotmap[out]:
            asm_code.add(asm_cmds.Mov(spotmap[out], temp, size))


class Add(_AddMult):
    """ADD - adds arg1 and arg2, then saves to output.

    IL values output, arg1, arg2 must all have the same type. No type
    conversion or promotion is done here.

    """

    def __init__(self, output, arg1, arg2): # noqa D102
        self.output = output
        self.arg1 = arg1
        self.arg2 = arg2

        self._assert_same_ctype([output, arg1, arg2])

    def inputs(self): # noqa D102
        return [self.arg1, self.arg2]

    def outputs(self): # noqa D102
        return [self.output]

    def rel_spot_pref(self): # noqa D102
        return {self.output: [self.arg1, self.arg2]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        self._shared_asm(asm_cmds.Add, True, self.output, self.arg1, self.arg2,
                         spotmap, get_reg, asm_code)


class Subtr(_AddMult):
    """SUBTR - Subtracts arg1 and arg2, then saves to output.

    ILValues output, arg1, and arg2 must all have types of the same size.
    """

    def __init__(self, output, arg1, arg2): # noqa D102
        self.out = output
        self.arg1 = arg1
        self.arg2 = arg2

    def inputs(self): # noqa D102
        return [self.arg1, self.arg2]

    def outputs(self): # noqa D102
        return [self.out]

    def rel_spot_pref(self): # noqa D102
        return {self.out: [self.arg1]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        self._shared_asm(asm_cmds.Sub, False, self.out, self.arg1, self.arg2,
                         spotmap, get_reg, asm_code)


class Mult(_AddMult):
    """MULT - multiplies arg1 and arg2, then saves to output.

    IL values output, arg1, arg2 must all have the same type. No type
    conversion or promotion is done here.

    """

    def __init__(self, output, arg1, arg2):  # noqa D102
        self.output = output
        self.arg1 = arg1
        self.arg2 = arg2

        self._assert_same_ctype([output, arg1, arg2])

    def inputs(self): # noqa D102
        return [self.arg1, self.arg2]

    def outputs(self): # noqa D102
        return [self.output]

    def clobber(self):  # noqa D102
        return [spots.RAX, spots.RDX] if not self.output.ctype.signed else []

    def rel_spot_pref(self):  # noqa D102
        if self.output.ctype.signed:
            return {self.output: [self.arg1, self.arg2]}
        else:
            return {}

    def abs_spot_pref(self):  # noqa D102
        if not self.output.ctype.signed:
            return {self.output: [spots.RAX],
                    self.arg1: [spots.RAX],
                    self.arg2: [spots.RAX]}
        else:
            return {}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        ctype = self.arg1.ctype

        # Unsigned multiplication
        if not ctype.signed:
            arg1_spot = spotmap[self.arg1]
            arg2_spot = spotmap[self.arg2]
            size = ctype.size

            if arg1_spot == spots.RAX:
                mul_spot = arg2_spot
            elif arg2_spot == spots.RAX:
                mul_spot = arg1_spot
            else:
                # If either is literal, move that one to RAX
                if self._is_imm(arg2_spot):
                    asm_code.add(asm_cmds.Mov(spots.RAX, arg2_spot, size))
                    mul_spot = arg1_spot
                else:
                    asm_code.add(asm_cmds.Mov(spots.RAX, arg1_spot, size))
                    mul_spot = arg2_spot

            # Operand is an immediate, move it to a register
            if self._is_imm(mul_spot):
                r = get_reg([], [spots.RAX])
                asm_code.add(asm_cmds.Mov(r, mul_spot, ctype.size))
                mul_spot = r

            asm_code.add(asm_cmds.Mul(mul_spot, None, ctype.size))

            if spotmap[self.output] != spots.RAX:
                asm_code.add(
                    asm_cmds.Mov(spotmap[self.output], spots.RAX, ctype.size))

        # Signed multiplication
        else:
            self._shared_asm(asm_cmds.Imul, True, self.output, self.arg1,
                             self.arg2, spotmap, get_reg, asm_code)


class Div(ILCommand):
    """DIV - divides arg1 and arg2, then saves to output.

    IL values output, arg1, arg2 must all have the same type of size at least
    int. No type conversion or promotion is done here.

    """

    def __init__(self, output, arg1, arg2): # noqa D102
        self.output = output
        self.arg1 = arg1
        self.arg2 = arg2

        self._assert_same_ctype([output, arg1, arg2])

    def inputs(self): # noqa D102
        return [self.arg1, self.arg2]

    def outputs(self): # noqa D102
        return [self.output]

    def clobber(self): # noqa D102
        return [spots.RAX, spots.RDX]

    def abs_spot_pref(self): # noqa D102
        return {self.output: [spots.RAX],
                self.arg1: [spots.RAX]}

    def abs_spot_conf(self): # noqa D102
        return {self.arg2: [spots.RDX, spots.RAX]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        ctype = self.arg1.ctype
        size = ctype.size

        output_spot = spotmap[self.output]
        arg1_spot = spotmap[self.arg1]
        arg2_spot = spotmap[self.arg2]

        # Move first operand into RAX if we can do so without clobbering
        # other argument
        moved_to_rax = False
        if spotmap[self.arg1] != spots.RAX and spotmap[self.arg2] != spots.RAX:
            moved_to_rax = True
            asm_code.add(asm_cmds.Mov(spots.RAX, arg1_spot, size))

        # If the divisor is a literal or in a bad register, we must move it
        # to a register.
        if (self._is_imm(spotmap[self.arg2]) or
             spotmap[self.arg2] in [spots.RAX, spots.RDX]):
            r = get_reg([], [spots.RAX, spots.RDX])
            asm_code.add(asm_cmds.Mov(r, arg2_spot, size))
            arg2_final_spot = r
        else:
            arg2_final_spot = arg2_spot

        # If we did not move to RAX above, do so here.
        if not moved_to_rax and arg1_spot != spots.RAX:
            asm_code.add(asm_cmds.Mov(spots.RAX, arg1_spot, size))

        if ctype.signed:
            if ctype.size == 4:
                asm_code.add(asm_cmds.Cdq())
            elif ctype.size == 8:
                asm_code.add(asm_cmds.Cqo())
            asm_code.add(asm_cmds.Idiv(arg2_final_spot, None, size))
        else:
            # zero out RDX register
            asm_code.add(asm_cmds.Xor(spots.RDX, spots.RDX, size))
            asm_code.add(asm_cmds.Div(arg2_final_spot, None, size))

        if spotmap[self.output] != spots.RAX:
            asm_code.add(asm_cmds.Mov(output_spot, spots.RAX, size))
