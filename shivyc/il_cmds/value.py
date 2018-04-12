"""IL commands for setting/reading values and getting value addresses."""

import shivyc.asm_cmds as asm_cmds
import shivyc.ctypes as ctypes
import shivyc.spots as spots
from shivyc.il_cmds.base import ILCommand
from shivyc.spots import RegSpot, MemSpot, LiteralSpot


class _ValueCmd(ILCommand):
    """Abstract base class for value commands.

    This class defines a helper function for moving data from one location
    to another.
    """
    def move_data(self, target_spot, start_spot, size, reg, asm_code):
        """Emits code to move data from start to target.

        Given a target spot, start spot, size of data to move,
        and a register that can be clobbered in the move, this function
        emits code to move all the data. It is efficient whether the input
        spots are registers or memory, and in particular this function
        works even if the input size is not in {1, 2, 4, 8}.

        The given register is used as an intermediary for transferring
        values between the target_spot and start_spot. It is *always* safe
        for `reg` to be one of these two, and in fact it is recommended
        that if either of target_spot or start_spot is a register then
        `reg` be equal to that.
        """
        # TODO: consider padding everything to 8 bytes to reduce the
        # number of mov operations emitted for struct copying.
        shift = 0
        while shift < size:
            reg_size = self._reg_size(size - shift)
            start_spot = start_spot.shift(shift)
            target_spot = target_spot.shift(shift)

            if isinstance(start_spot, LiteralSpot):
                reg = start_spot
            elif reg != start_spot:
                asm_code.add(asm_cmds.Mov(reg, start_spot, reg_size))

            if reg != target_spot:
                asm_code.add(asm_cmds.Mov(target_spot, reg, reg_size))

            shift += reg_size

    def _reg_size(self, size):
        """Return largest register size that does not overfit given size."""
        reg_sizes = [8, 4, 2, 1]
        for reg_size in reg_sizes:
            if size >= reg_size:
                return reg_size


class LoadArg(ILCommand):
    """Loads a function argument value into an IL value.

    output is the IL value to load the function argument value into,
    and arg_num is the index of the argument to load. For example,
    at the start of the body of the following function:

       int func(int a, int b);

    the following two LoadArg commands would be appropriate

       LoadArg(a, 0)
       LoadArg(b, 1)

    in order to load the first function argument into the variable a and
    the second function argument into the variable b.
    """
    arg_regs = [spots.RDI, spots.RSI, spots.RDX, spots.RCX, spots.R8, spots.R9]

    def __init__(self, output, arg_num):
        self.output = output
        self.arg_reg = self.arg_regs[arg_num]

    def inputs(self):
        return []

    def outputs(self):
        return [self.output]

    def clobber(self):
        return [self.arg_reg]

    def abs_spot_pref(self):
        return {self.output: [self.arg_reg]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):
        if spotmap[self.output] == self.arg_reg:
            return
        else:
            asm_code.add(asm_cmds.Mov(
                spotmap[self.output], self.arg_reg, self.output.ctype.size))


class Set(_ValueCmd):
    """SET - sets output IL value to arg IL value.

    SET converts between all scalar types, so the output and arg IL values
    need not have the same type if both are scalar types. If either one is
    a struct type, the other must be the same struct type.

    TODO: split this up into finer IL commands.
    """
    def __init__(self, output, arg): # noqa D102
        self.output = output
        self.arg = arg

    def inputs(self): # noqa D102
        return [self.arg]

    def outputs(self): # noqa D102
        return [self.output]

    def rel_spot_pref(self): # noqa D102
        if self.output.ctype.weak_compat(ctypes.bool_t):
            return {}
        else:
            return {self.output: [self.arg]}

    def rel_spot_conf(self):
        if self.output.ctype.weak_compat(ctypes.bool_t):
            return {self.output: [self.arg]}
        else:
            return {}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        if self.output.ctype.weak_compat(ctypes.bool_t):
            return self._set_bool(spotmap, get_reg, asm_code)

        elif isinstance(spotmap[self.arg], LiteralSpot):
            out_spot = spotmap[self.output]
            arg_spot = spotmap[self.arg]
            size = self.output.ctype.size
            asm_code.add(asm_cmds.Mov(out_spot, arg_spot, size))

        elif self.output.ctype.size <= self.arg.ctype.size:
            if spotmap[self.output] == spotmap[self.arg]:
                return

            if isinstance(spotmap[self.output], RegSpot):
                r = spotmap[self.output]
            elif isinstance(spotmap[self.arg], RegSpot):
                r = spotmap[self.arg]
            else:
                r = get_reg()

            self.move_data(spotmap[self.output], spotmap[self.arg],
                           self.output.ctype.size, r, asm_code)

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

        # If arg_asm is a LITERAL or conflicts with output, move to register.
        if (isinstance(spotmap[self.arg], LiteralSpot)
              or spotmap[self.arg] == spotmap[self.output]):
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


class ReadAt(_ValueCmd):
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

        if isinstance(addr_spot, RegSpot):
            addr_r = addr_spot
        else:
            addr_r = get_reg([], [output_spot])
            asm_code.add(asm_cmds.Mov(addr_r, addr_spot, 8))

        indir_spot = MemSpot(addr_r)
        if isinstance(output_spot, RegSpot):
            temp_reg = output_spot
        else:
            temp_reg = get_reg([], [addr_r])

        self.move_data(output_spot, indir_spot, self.output.ctype.size,
                       temp_reg, asm_code)


class SetAt(_ValueCmd):
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
        addr_spot = spotmap[self.addr]
        value_spot = spotmap[self.val]

        if isinstance(addr_spot, RegSpot):
            addr_r = addr_spot
        else:
            addr_r = get_reg([], [value_spot])
            asm_code.add(asm_cmds.Mov(addr_r, addr_spot, 8))

        indir_spot = MemSpot(addr_r)
        if isinstance(value_spot, RegSpot):
            temp_reg = value_spot
        else:
            temp_reg = get_reg([], [addr_r])

        self.move_data(indir_spot, value_spot, self.val.ctype.size,
                       temp_reg, asm_code)


class _RelCommand(_ValueCmd):
    """Parent class for the relative commands."""

    def __init__(self, val, base, chunk, count):  # noqa D102
        self.val = val
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
        r = get_reg([], [spotmap[self.val]] + self._used_regs)
        self._used_regs.append(r)

        count_size = self.count.ctype.size
        asm_code.add(asm_cmds.Mov(r, spotmap[self.count], count_size))

        return spotmap[self.base].shift(self.chunk, r)

    def get_reg_spot(self, reg_val, spotmap, get_reg):
        """Get a register or literal spot for self.reg_val."""

        if (isinstance(spotmap[reg_val], LiteralSpot) or
             isinstance(spotmap[reg_val], RegSpot)):
            return spotmap[reg_val]

        val_spot = get_reg([], [spotmap[self.count]] + self._used_regs)
        self._used_regs.append(val_spot)
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
        if self.count:
            return [self.val, self.base, self.count]
        else:
            return [self.base, self.val]

    def outputs(self):  # noqa D102
        return []

    def references(self):  # noqa D102
        return {None: [self.base]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        if not isinstance(spotmap[self.base], MemSpot):
            raise NotImplementedError("expected base in memory spot")

        rel_spot = self.get_rel_spot(spotmap, get_reg, asm_code)
        reg = self.get_reg_spot(self.val, spotmap, get_reg)

        val_size = self.val.ctype.size
        self.move_data(rel_spot, spotmap[self.val], val_size, reg, asm_code)


class AddrRel(_RelCommand):
    """Gets the address of a location relative to a given object.

    For further documentation, see SetRel.

    """
    def __init__(self, output, base, chunk=0, count=None):  # noqa D102
        super().__init__(output, base, chunk, count)
        self.output = output

    def inputs(self):  # noqa D102
        return [self.base, self.count] if self.count else [self.base]

    def outputs(self):  # noqa D102
        return [self.output]

    def references(self):  # noqa D102
        return {self.output: [self.base]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        if not isinstance(spotmap[self.base], MemSpot):
            raise NotImplementedError("expected base in memory spot")

        rel_spot = self.get_rel_spot(spotmap, get_reg, asm_code)
        out_spot = self.get_reg_spot(self.output, spotmap, get_reg)
        asm_code.add(asm_cmds.Lea(out_spot, rel_spot))

        if out_spot != spotmap[self.output]:
            asm_code.add(asm_cmds.Mov(spotmap[self.output], out_spot, 8))


class ReadRel(_RelCommand):
    """Reads the value at a location relative to a given object.

    For further documentation, see SetRel.

    """

    def __init__(self, output, base, chunk=0, count=None):  # noqa D102
        super().__init__(output, base, chunk, count)
        self.output = output

    def inputs(self):  # noqa D102
        return [self.base, self.count] if self.count else [self.base]

    def outputs(self):  # noqa D102
        return [self.output]

    def references(self):  # noqa D102
        return {None: [self.base]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        if not isinstance(spotmap[self.base], MemSpot):
            raise NotImplementedError("expected base in memory spot")

        rel_spot = self.get_rel_spot(spotmap, get_reg, asm_code)
        reg = self.get_reg_spot(self.output, spotmap, get_reg)

        out_size = self.output.ctype.size
        self.move_data(spotmap[self.output], rel_spot, out_size, reg, asm_code)
