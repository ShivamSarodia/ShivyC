"""IL commands for setting/reading values and getting value addresses."""

import shivyc.asm_cmds as asm_cmds
import shivyc.ctypes as ctypes
from shivyc.il_cmds.base import ILCommand
from shivyc.spots import RegSpot, MemSpot, LiteralSpot


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
        elif isinstance(spotmap[self.arg], LiteralSpot):
            out_spot = spotmap[self.output]
            arg_spot = spotmap[self.arg]
            size = self.output.ctype.size
            asm_code.add(asm_cmds.Mov(out_spot, arg_spot, size))
        elif self.output.ctype.size <= self.arg.ctype.size:
            if spotmap[self.output] == spotmap[self.arg]:
                return

            output_spot = spotmap[self.output]

            if isinstance(output_spot, RegSpot):
                r = output_spot
            elif isinstance(spotmap[self.arg], RegSpot):
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
        if isinstance(spotmap[self.arg], LiteralSpot):
            r = get_reg([], [spotmap[self.output]])
            asm_code.add(
                asm_cmds.Mov(r, spotmap[self.arg], self.arg.ctype.size))
            arg_spot = r
        else:
            arg_spot = spotmap[self.arg]

        label = asm_code.get_label()
        output_spot = spotmap[self.output]

        zero = LiteralSpot("0")
        one = LiteralSpot("1")

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

        if isinstance(spotmap[self.addr], RegSpot):
            indir_spot = MemSpot(spotmap[self.addr])
        else:
            r = get_reg()
            asm_code.add(asm_cmds.Mov(r, addr_spot, 8))
            indir_spot = MemSpot(r)

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
        if isinstance(spotmap[self.addr], RegSpot):
            indir_spot = MemSpot(spotmap[self.addr])
        else:
            r = get_reg([], [spotmap[self.val]])
            asm_code.add(asm_cmds.Mov(r, spotmap[self.addr], 8))
            indir_spot = MemSpot(r)

        asm_code.add(
            asm_cmds.Mov(indir_spot, spotmap[self.val], size))


class _RelCommand(ILCommand):
    """Parent class for the relative commands."""

    def __init__(self, reg_val, base, chunk, count):  # noqa D102
        self.reg_val = reg_val
        self.base = base
        self.chunk = chunk
        self.count = count

        # Keep track of which registers have been used from a call to
        # get_reg so we don't accidentally reuse them.
        self._used_regs = []

    def get_rel_spot(self, spotmap, get_reg, asm_code):
        """Get a relative spot for the relative value."""

        # If there's no count, we only need to shift by the chunk
        if not self.count:
            return spotmap[self.base].shift(self.chunk)

        # If there is a count in a literal spot, we're good to go. Also,
        # if count is already in a register, we're good to go by just using
        # that register for the count. (Because we require the count be 32-
        # or 64-bit, we know the full register stores exactly the value of
        # count).
        if (isinstance(spotmap[self.count], LiteralSpot) or
             isinstance(spotmap[self.count], RegSpot)):
            return spotmap[self.base].shift(self.chunk, spotmap[self.count])

        # Otherwise, move count to a register.
        r = get_reg([], [spotmap[self.reg_val]] + self._used_regs)
        self._used_regs.append(r)

        count_size = self.count.ctype.size
        asm_code.add(asm_cmds.Mov(r, spotmap[self.count], count_size))

        return spotmap[self.base].shift(self.chunk, r)

    def get_reg_spot(self, spotmap, get_reg, asm_code):
        """Get a register or literal spot for self.reg_val."""

        if (isinstance(spotmap[self.reg_val], LiteralSpot) or
             isinstance(spotmap[self.reg_val], RegSpot)):
            return spotmap[self.reg_val]

        val_spot = get_reg([], [spotmap[self.count]] + self._used_regs)
        self._used_regs.append(val_spot)

        val_size = self.reg_val.ctype.size
        asm_code.add(asm_cmds.Mov(val_spot, spotmap[self.reg_val], val_size))
        return val_spot


class SetRel(_RelCommand):
    """Sets value relative to given object.

    val - ILValue representing the value to set at given location.

    base - ILValue representing the base object. Note this is the base
    object itself, not the address of the base object.

    chunk - A Python integer representing the size of each chunk of offset
    (see below for a more clear explanation)

    count - If provided, a 64-bit integral ILValue representing the
    number of chunks of offset. If this value is provided, then `chunk`
    must be in {1, 2, 4, 8}.

    In summary, if `count` is provided, then the address of the object
    represented by this LValue is:

        &base + chunk * count

    and if `count` is not provided, the address is just

        &base + chunk
    """

    def __init__(self, val, base, chunk=0, count=None):  # noqa D102
        super().__init__(val, base, chunk, count)
        self.val = val

    def inputs(self):  # noqa D102
        return [self.val, self.base, self.count]

    def outputs(self):  # noqa D102
        return []

    def references(self):  # noqa D102
        return {None: [self.base]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        if not isinstance(spotmap[self.base], MemSpot):
            raise NotImplementedError("expected base in memory spot")

        rel_spot = self.get_rel_spot(spotmap, get_reg, asm_code)
        val_spot = self.get_reg_spot(spotmap, get_reg, asm_code)
        asm_code.add(asm_cmds.Mov(rel_spot, val_spot, self.val.ctype.size))


class AddrRel(_RelCommand):
    """Gets the address of a location relative to a given object.

    For further documentation, see SetRel.

    """
    def __init__(self, output, base, chunk=0, count=None):  # noqa D102
        super().__init__(output, base, chunk, count)
        self.output = output

    def inputs(self):  # noqa D102
        return [self.base, self.count]

    def outputs(self):  # noqa D102
        return [self.output]

    def references(self):  # noqa D102
        return {self.output: [self.base]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        if not isinstance(spotmap[self.base], MemSpot):
            raise NotImplementedError("expected base in memory spot")

        rel_spot = self.get_rel_spot(spotmap, get_reg, asm_code)
        out_spot = self.get_reg_spot(spotmap, get_reg, asm_code)
        asm_code.add(asm_cmds.Lea(out_spot, rel_spot))


class ReadRel(_RelCommand):
    """Reads the value at a location relative to a given object.

    For further documentation, see SetRel.

    """

    def __init__(self, output, base, chunk=0, count=None):  # noqa D102
        super().__init__(output, base, chunk, count)
        self.output = output

    def inputs(self):  # noqa D102
        return [self.base, self.count]

    def outputs(self):  # noqa D102
        return [self.output]

    def references(self):  # noqa D102
        return {None: [self.base]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        if not isinstance(spotmap[self.base], MemSpot):
            raise NotImplementedError("expected base in memory spot")

        rel_spot = self.get_rel_spot(spotmap, get_reg, asm_code)
        out_spot = self.get_reg_spot(spotmap, get_reg, asm_code)
        asm_code.add(asm_cmds.Mov(out_spot, rel_spot, self.output.ctype.size))
