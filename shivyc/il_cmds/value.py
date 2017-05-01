"""IL commands for setting/reading values and getting value addresses."""

import shivyc.asm_cmds as asm_cmds
import shivyc.ctypes as ctypes
from shivyc.il_cmds.base import ILCommand
from shivyc.spots import Spot


class Set(ILCommand):
    """SET - sets output IL value to arg IL value.

    The output IL value and arg IL value need not have the same type. The SET
    command will generate code to convert them as necessary.

    """

    def __init__(self, output, arg): # noqa D102
        self.output = output
        self.arg = arg

    def inputs(self): # noqa D102
        return [self.arg]

    def outputs(self): # noqa D102
        return [self.output]

    def rel_spot_pref(self): # noqa D102
        return {self.output: [self.arg]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        if self.output.ctype == ctypes.bool_t:
            return self._set_bool(spotmap, get_reg, asm_code)
        elif spotmap[self.arg].spot_type == Spot.LITERAL:
            out_spot = spotmap[self.output]
            arg_spot = spotmap[self.arg]
            size = self.output.ctype.size
            asm_code.add(asm_cmds.Mov(out_spot, arg_spot, size))
        elif self.output.ctype.size <= self.arg.ctype.size:
            if spotmap[self.output] == spotmap[self.arg]:
                return

            output_spot = spotmap[self.output]

            if output_spot.spot_type == Spot.REGISTER:
                r = output_spot
            elif spotmap[self.arg].spot_type == Spot.REGISTER:
                r = spotmap[self.arg]
            else:
                r = get_reg()

            size = self.output.ctype.size
            if r != spotmap[self.arg]:
                asm_code.add(asm_cmds.Mov(r, spotmap[self.arg], size))

            if r != spotmap[self.output]:
                asm_code.add(asm_cmds.Mov(output_spot, r, size))

        else:
            r = get_reg([spotmap[self.output], spotmap[self.arg]])

            # Move from arg_asm -> r_asm
            if self.arg.ctype.signed:
                asm_code.add(asm_cmds.Movsx(r, spotmap[self.arg],
                                            self.output.ctype.size,
                                            self.arg.ctype.size))
            elif self.arg.ctype.size == 4:
                asm_code.add(asm_cmds.Mov(r, spotmap[self.arg], 4))
            else:
                asm_code.add(asm_cmds.Movzx(r, spotmap[self.arg],
                                            self.output.ctype.size,
                                            self.arg.ctype.size))

            # If necessary, move from r_asm -> output_asm
            if r != spotmap[self.output]:
                asm_code.add(asm_cmds.Mov(spotmap[self.output],
                                          r, self.output.ctype.size))

    def _set_bool(self, spotmap, get_reg, asm_code):
        """Emit code for SET command if arg is boolean type."""
        # When any scalar value is converted to _Bool, the result is 0 if the
        # value compares equal to 0; otherwise, the result is 1

        # If arg_asm is a LITERAL, move to register.
        if spotmap[self.arg].spot_type == Spot.LITERAL:
            r = get_reg([], [spotmap[self.output]])
            asm_code.add(
                asm_cmds.Mov(r, spotmap[self.arg], self.arg.ctype.size))
            arg_spot = r
        else:
            arg_spot = spotmap[self.arg]

        label = asm_code.get_label()
        output_spot = spotmap[self.output]

        zero = Spot(Spot.LITERAL, "0")
        one = Spot(Spot.LITERAL, "1")

        asm_code.add(asm_cmds.Mov(output_spot, zero, self.output.ctype.size))
        asm_code.add(asm_cmds.Cmp(arg_spot, zero, self.arg.ctype.size))
        asm_code.add(asm_cmds.Je(label))
        asm_code.add(asm_cmds.Mov(output_spot, one, self.output.ctype.size))
        asm_code.add(asm_cmds.Label(label))


class AddrOf(ILCommand):
    """Gets address of given variable.

    `output` must have type pointer to the type of `var`.

    """

    def __init__(self, output, var):  # noqa D102
        self.output = output
        self.var = var

    def inputs(self):  # noqa D102
        return [self.var]

    def outputs(self):  # noqa D102
        return [self.output]

    def references(self):  # noqa D102
        return {self.output: [self.var]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        r = get_reg([spotmap[self.output]])
        asm_code.add(asm_cmds.Lea(r, home_spots[self.var]))

        if r != spotmap[self.output]:
            size = self.output.ctype.size
            asm_code.add(asm_cmds.Mov(spotmap[self.output], r, size))


class ReadAt(ILCommand):
    """Reads value at given address.

    `addr` must have type pointer to the type of `output`

    """

    def __init__(self, output, addr):  # noqa D102
        self.output = output
        self.addr = addr

    def inputs(self):  # noqa D102
        return [self.addr]

    def outputs(self):  # noqa D102
        return [self.output]

    def indir_read(self):  # noqa D102
        return [self.addr]

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        addr_spot = spotmap[self.addr]
        output_spot = spotmap[self.output]

        if spotmap[self.addr].spot_type == Spot.REGISTER:
            indir_spot = Spot(Spot.MEM, (spotmap[self.addr], 0))
        else:
            r = get_reg()
            asm_code.add(asm_cmds.Mov(r, addr_spot, 8))
            indir_spot = Spot(Spot.MEM, (r, 0))

        size = self.output.ctype.size
        asm_code.add(asm_cmds.Mov(output_spot, indir_spot, size))


class SetAt(ILCommand):
    """Sets value at given address.

    `addr` must have type pointer to the type of `val`

    """

    def __init__(self, addr, val):  # noqa D102
        self.addr = addr
        self.val = val

    def inputs(self):  # noqa D102
        return [self.addr, self.val]

    def outputs(self):  # noqa D102
        return []

    def indir_write(self):  # noqa D102
        return [self.addr]

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        size = self.val.ctype.size
        if spotmap[self.addr].spot_type == Spot.REGISTER:
            indir_spot = Spot(Spot.MEM, (spotmap[self.addr], 0))
        else:
            r = get_reg([], [spotmap[self.val]])
            asm_code.add(asm_cmds.Mov(r, spotmap[self.addr], 8))
            indir_spot = Spot(Spot.MEM, (r, 0))

        asm_code.add(
            asm_cmds.Mov(indir_spot, spotmap[self.val], size))
