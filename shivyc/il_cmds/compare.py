"""IL commands for comparisons."""

import shivyc.asm_cmds as asm_cmds
from shivyc.il_cmds.base import ILCommand
from shivyc.spots import MemSpot, LiteralSpot


class _GeneralCmp(ILCommand):
    """_GeneralCmp - base class for the comparison commands.

    IL value output must have int type. arg1, arg2 must have types that can
    be compared for equality bit-by-bit. No type conversion or promotion is
    done here.

    """
    signed_cmp_cmd = None
    unsigned_cmp_cmd = None

    def __init__(self, output, arg1, arg2): # noqa D102
        self.output = output
        self.arg1 = arg1
        self.arg2 = arg2

    def inputs(self): # noqa D102
        return [self.arg1, self.arg2]

    def outputs(self): # noqa D102
        return [self.output]

    def rel_spot_conf(self):  # noqa D102
        return {self.output: [self.arg1, self.arg2]}

    def _fix_both_literal_or_mem(self, arg1_spot, arg2_spot, regs,
                                 get_reg, asm_code):
        """Fix arguments if both are literal or memory.

        Adds any called registers to given regs list. Returns tuple where
        first element is new spot of arg1 and second element is new spot of
        arg2.
        """
        if ((isinstance(arg1_spot, LiteralSpot) and
             isinstance(arg2_spot, LiteralSpot)) or
            (isinstance(arg1_spot, MemSpot) and
             isinstance(arg2_spot, MemSpot))):

            # No need to worry about r overlapping with arg1 or arg2 because
            # in this case both are literal/memory.
            r = get_reg([], regs)
            regs.append(r)
            asm_code.add(asm_cmds.Mov(r, arg1_spot, self.arg1.ctype.size))
            return r, arg2_spot
        else:
            return arg1_spot, arg2_spot

    def _fix_either_literal64(self, arg1_spot, arg2_spot, regs,
                              get_reg, asm_code):
        """Move any 64-bit immediate operands to register."""

        if self._is_imm64(arg1_spot):
            size = self.arg1.ctype.size
            new_arg1_spot = get_reg([], regs + [arg2_spot])
            asm_code.add(asm_cmds.Mov(new_arg1_spot, arg1_spot, size))
            return new_arg1_spot, arg2_spot

        # We cannot have both cases because _fix_both_literal is called
        # before this.
        elif self._is_imm64(arg2_spot):
            size = self.arg2.ctype.size
            new_arg2_spot = get_reg([], regs + [arg1_spot])
            asm_code.add(asm_cmds.Mov(new_arg2_spot, arg2_spot, size))
            return arg1_spot, new_arg2_spot
        else:
            return arg1_spot, arg2_spot

    def _fix_literal_wrong_order(self, arg1_spot, arg2_spot):
        """If the first operand is a literal, swap the operands."""
        if self._is_imm(arg1_spot):
            return arg2_spot, arg1_spot
        else:
            return arg1_spot, arg2_spot

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        regs = []

        result = get_reg([spotmap[self.output]],
                         [spotmap[self.arg1], spotmap[self.arg2]])
        regs.append(result)

        out_size = self.output.ctype.size
        eq_val_spot = LiteralSpot(1)
        asm_code.add(asm_cmds.Mov(result, eq_val_spot, out_size))

        arg1_spot, arg2_spot = self._fix_both_literal_or_mem(
            spotmap[self.arg1], spotmap[self.arg2], regs, get_reg, asm_code)
        arg1_spot, arg2_spot = self._fix_either_literal64(
            arg1_spot, arg2_spot, regs, get_reg, asm_code)
        arg1_spot, arg2_spot = self._fix_literal_wrong_order(
            arg1_spot, arg2_spot)

        arg_size = self.arg1.ctype.size
        neq_val_spot = LiteralSpot(0)
        label = asm_code.get_label()

        asm_code.add(asm_cmds.Cmp(arg1_spot, arg2_spot, arg_size))
        asm_code.add(self.cmp_command()(label))
        asm_code.add(asm_cmds.Mov(result, neq_val_spot, out_size))
        asm_code.add(asm_cmds.Label(label))

        if result != spotmap[self.output]:
            asm_code.add(asm_cmds.Mov(spotmap[self.output], result, out_size))

    def cmp_command(self):
        ctype = self.arg1.ctype
        if ctype.is_pointer() or (ctype.is_integral() and not ctype.signed):
            return self.unsigned_cmp_cmd
        else:
            return self.signed_cmp_cmd


class NotEqualCmp(_GeneralCmp):
    """NotEqualCmp - checks whether arg1 and arg2 are not equal.

    IL value output must have int type. arg1, arg2 must all have the same
    type. No type conversion or promotion is done here.

    """
    signed_cmp_cmd = asm_cmds.Jne
    unsigned_cmp_cmd = asm_cmds.Jne


class EqualCmp(_GeneralCmp):
    """EqualCmp - checks whether arg1 and arg2 are equal.

    IL value output must have int type. arg1, arg2 must all have the same
    type. No type conversion or promotion is done here.

    """
    signed_cmp_cmd = asm_cmds.Je
    unsigned_cmp_cmd = asm_cmds.Je


class LessCmp(_GeneralCmp):
    signed_cmp_cmd = asm_cmds.Jl
    unsigned_cmp_cmd = asm_cmds.Jb


class GreaterCmp(_GeneralCmp):
    signed_cmp_cmd = asm_cmds.Jg
    unsigned_cmp_cmd = asm_cmds.Ja


class LessOrEqCmp(_GeneralCmp):
    signed_cmp_cmd = asm_cmds.Jle
    unsigned_cmp_cmd = asm_cmds.Jbe


class GreaterOrEqCmp(_GeneralCmp):
    signed_cmp_cmd = asm_cmds.Jge
    unsigned_cmp_cmd = asm_cmds.Jae
