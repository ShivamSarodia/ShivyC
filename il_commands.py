"""Classes representing IL commands.

Each IL command is represented by a class that inherits from the ILCommand
interface. The implementation provides code that generates ASM for each IL
command.

For arithmetic commands like Add or Mult, the arguments and output must all be
pre-cast to the same type. In addition, this type must be size `int` or greater
per the C spec. The Set command is exempt from this requirement, and can be
used to cast.

"""

import ctypes
import spots
from il_gen import CType
from spots import Spot


class ILCommand:
    """Base interface for all IL commands."""

    def inputs(self):
        """Return list of ILValues used as input for this command."""
        raise NotImplementedError

    def outputs(self):
        """Return list of values output by this command.

        No command executed after this one should rely on the previous value of
        any ILValue in the list returned here. ("Previous value" denotes the
        value of the ILValue before this command was executed.)
        """
        raise NotImplementedError

    def clobber(self):
        """Return list of Spots this command may clobber, other than outputs.

        Every Spot this command may change the value at (not including
        the Spots of the outputs returned above) must be included in the
        return list of this function. For example, signed division clobbers
        RAX and RDX.
        """
        return []

    def rel_spot_pref(self):
        """Return the relative spot preference list (RSPL) for this command.

        A RSPL is a dictionary mapping an ILValue to a list of ILValues. For
        each key k in the RSPL, the register allocator will attempt to place k
        in the same spot as an ILValue in RSPL[k] is placed. RSPL[k] is
        ordered by preference; that is, the register allocator will
        first attempt to place k in the same spot as RSPL[k][0], then the
        same spot as RSPL[k][1], etc.
        """
        return {}

    def abs_spot_pref(self):
        """Return the absolute spot preference list (ASPL) for this command.

        An ASPL is a dictionary mapping an ILValue to a list of Spots. For
        each key k in the ASPL, the register allocator will attempt to place k
        in one of the spots listed in ASPL[k]. ASPL[k] is ordered by
        preference; that is, the register allocator will first attempt to
        place k in ASPL[k][0], then in ASPL[k][1], etc.
        """
        return {}

    def references(self):
        """Return the potential reference list (PRL) for this command.

        The PRL is a dictionary mapping an ILValue to a list of ILValues.
        If this command may directly set some ILValue k to be a pointer to
        other ILValue(s) v1, v2, etc., then PRL[k] must include v1, v2,
        etc. That is, suppose the PRL was {t1: [t2]}. This means that
        ILValue t1 output from this command may be a pointer to the ILValue t2.
        """
        return {}

    def indir_write(self):
        """Return list of values that may be dereferenced for indirect write.

        For example, suppose this list is [t1, t2]. Then, this command may
        be changing the value of the ILValue pointed to by t1 or the value
        of the ILValue pointed to by t2.
        """
        return []

    def indir_read(self):
        """Return list of values that may be dereferenced for indirect read.

        For example, suppose this list is [t1, t2]. Then, this command may
        be reading the value of the ILValue pointed to by t1 or the value of
        the ILValue pointed to by t2.
        """
        return []

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):
        """Generate assembly code for this command.

        spotmap - Dictionary mapping every input and output ILValue to a spot.

        home_spots - Dictionary mapping every ILValue that appears in any of
        self.references().values() to a memory spot. This is used for
        commands which need the address of an ILValue.

        get_reg - Function to get a usable register. Accepts two arguments,
        first is a list of Spot preferences, and second is a list of
        unacceptable spots. This function returns a register which is not
        in the list of unacceptable spots and can be clobbered. Note this
        could be one of the registers the input is stored in, if the input
        ILValues are not being used after this command executes.

        asm_code - ASMCode object to add code to

        returns - Dictionary mapping an ILValue to a list of spots. For each
        ILValue V copied to a new spot S in this function, S should be in the
        list keyed by V. This allows the register allocator to potentially
        avoid unnecessary copies.
        """
        raise NotImplementedError

    def _assert_same_ctype(self, il_values):
        """Raise ValueError if all IL values do not have the same type."""
        ctype = None
        for il_value in il_values:
            if ctype and ctype != il_value.ctype:
                raise ValueError("different ctypes")  # pragma: no cover

    def _is_imm64(self, spot):
        """Return True iff given spot is a 64-bit immediate operand."""
        return (spot.spot_type == Spot.LITERAL and
                (int(spot.detail) > ctypes.int_max or
                 int(spot.detail) < ctypes.int_min))

    def to_str(self, name, inputs, output=None):  # pragma: no cover
        """Given the name, inputs, and outputs return its string form."""
        RED = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'

        input_str = "".join(str(input).ljust(40) for input in inputs)
        output_str = (str(output) if output else "").ljust(40)
        return output_str + RED + BOLD + str(name).ljust(10) + ENDC + " " + \
               input_str


class Add(ILCommand):
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
        moves = {}

        ctype = self.arg1.ctype
        output_asm = spotmap[self.output].asm_str(ctype.size)
        arg1_asm = spotmap[self.arg1].asm_str(ctype.size)
        arg2_asm = spotmap[self.arg2].asm_str(ctype.size)

        # Get temp register for computation.
        temp = get_reg([spotmap[self.output],
                        spotmap[self.arg1],
                        spotmap[self.arg2]])
        temp_asm = temp.asm_str(ctype.size)

        if temp == spotmap[self.arg1]:
            if not self._is_imm64(spotmap[self.arg2]):
                asm_code.add_command("add", temp_asm, arg2_asm)
            else:
                raise NotImplementedError
        elif temp == spotmap[self.arg2]:
            if not self._is_imm64(spotmap[self.arg1]):
                asm_code.add_command("add", temp_asm, arg1_asm)
            else:
                raise NotImplementedError
        else:
            if (not self._is_imm64(spotmap[self.arg1]) and
                 not self._is_imm64(spotmap[self.arg2])):
                moves[self.arg1] = [temp]
                asm_code.add_command("mov", temp_asm, arg1_asm)
                asm_code.add_command("add", temp_asm, arg2_asm)
            elif (self._is_imm64(spotmap[self.arg1]) and
                  not self._is_imm64(spotmap[self.arg2])):
                moves[self.arg1] = [temp]
                asm_code.add_command("mov", temp_asm, arg1_asm)
                asm_code.add_command("add", temp_asm, arg2_asm)
            elif (not self._is_imm64(spotmap[self.arg1]) and
                  self._is_imm64(spotmap[self.arg2])):
                moves[self.arg2] = [temp]
                asm_code.add_command("mov", temp_asm, arg2_asm)
                asm_code.add_command("add", temp_asm, arg1_asm)
            else:  # both are imm64
                raise NotImplementedError

        if temp != spotmap[self.output]:
            asm_code.add_command("mov", output_asm, temp_asm)

        return moves

    def __str__(self):    # pragma: no cover
        return self.to_str("ADD", [self.arg1, self.arg2], self.output)


class Mult(ILCommand):
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

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        ctype = self.arg1.ctype
        arg1_asm = spotmap[self.arg1].asm_str(ctype.size)
        arg2_asm = spotmap[self.arg2].asm_str(ctype.size)
        output_asm = spotmap[self.output].asm_str(ctype.size)
        rax_asm = spots.RAX.asm_str(ctype.size)

        asm_code.add_command("mov", rax_asm, arg1_asm)

        if ctype.signed:
            # If ctype is signed, then use signed multiplication
            asm_code.add_command("imul", rax_asm, arg2_asm)
        elif spotmap[self.arg2].spot_type == Spot.LITERAL:
            # If ctype is unsigned and literal, move to register and multiply
            arg2_final_asm = spots.RSI.asm_str(ctype.size)
            asm_code.add_command("mov", arg2_final_asm, arg2_asm)
            asm_code.add_command("mul", arg2_final_asm)
        else:
            # If ctype is unsigned and not literal, just multiply
            asm_code.add_command("mul", arg2_asm)

        asm_code.add_command("mov", output_asm, rax_asm)

    def __str__(self):    # pragma: no cover
        return self.to_str("MULT", [self.arg1, self.arg2], self.output)


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

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        ctype = self.arg1.ctype
        arg1_asm = spotmap[self.arg1].asm_str(ctype.size)
        arg2_asm = spotmap[self.arg2].asm_str(ctype.size)
        output_asm = spotmap[self.output].asm_str(ctype.size)
        rax_asm = spots.RAX.asm_str(ctype.size)

        # If the divisor is a literal, we must move it to a register.
        if spotmap[self.arg2].spot_type == Spot.LITERAL:
            arg2_final_asm = spots.RSI.asm_str(ctype.size)
            asm_code.add_command("mov", arg2_final_asm, arg2_asm)
        else:
            arg2_final_asm = arg2_asm

        asm_code.add_command("mov", rax_asm, arg1_asm)

        if ctype.signed:
            if ctype.size == 4:
                asm_code.add_command("cdq")  # sign extend EAX into EDX
            elif ctype.size == 8:
                asm_code.add_command("cqo")  # sign extend RAX into RDX
            asm_code.add_command("idiv", arg2_final_asm)
        else:
            # zero out RDX register
            rdx_asm = spots.RDX.asm_str(ctype.size)
            asm_code.add_command("xor", rdx_asm, rdx_asm)
            asm_code.add_command("div", arg2_final_asm)

        asm_code.add_command("mov", output_asm, rax_asm)

    def __str__(self):  # pragma: no cover
        return self.to_str("DIV", [self.arg1, self.arg2], self.output)


class _GeneralEqualCmp(ILCommand):
    """_GeneralEqualCmp - base class for EqualCmp and NotEqualCmp.

    IL value output must have int type. arg1, arg2 must have types that can
    be compared for equality bit-by-bit. No type conversion or promotion is
    done here.

    """

    def __init__(self, output, arg1, arg2): # noqa D102
        self.output = output
        self.arg1 = arg1
        self.arg2 = arg2

    def inputs(self): # noqa D102
        return [self.arg1, self.arg2]

    def outputs(self): # noqa D102
        return [self.output]

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        output_asm = spotmap[self.output].asm_str(self.output.ctype.size)
        arg1_spot = spotmap[self.arg1]
        arg2_spot = spotmap[self.arg2]

        asm_code.add_command("mov", output_asm, self.equal_value)

        # If both LITERAL or both MEM, move one to a register
        if ((arg1_spot.spot_type == Spot.LITERAL and
             arg2_spot.spot_type == Spot.LITERAL) or
            (arg1_spot.spot_type == Spot.MEM and
             arg2_spot.spot_type == Spot.MEM)):
            rax_asm = spots.RAX.asm_str(self.arg1.ctype.size)
            asm_code.add_command("mov", rax_asm,
                                 arg1_spot.asm_str(self.arg1.ctype.size))
            arg1_spot = spots.RAX

        # If either arg is 64-bit immediate, move to a register
        if ((arg1_spot.spot_type == Spot.LITERAL and
             self.arg1.ctype.size == 8)):
            rdx_asm = spots.RDX.asm_str(self.arg1.ctype.size)
            asm_code.add_command("mov", rdx_asm,
                                 arg1_spot.asm_str(self.arg1.ctype.size))
            arg1_spot = spots.RDX
        elif ((arg2_spot.spot_type == Spot.LITERAL and
               self.arg2.ctype.size == 8)):
            rdx_asm = spots.RDX.asm_str(self.arg2.ctype.size)
            asm_code.add_command("mov", rdx_asm,
                                 arg2_spot.asm_str(self.arg2.ctype.size))
            arg2_spot = spots.RDX

        label = asm_code.get_label()
        asm_code.add_command("cmp", arg1_spot.asm_str(self.arg1.ctype.size),
                             arg2_spot.asm_str(self.arg2.ctype.size))
        asm_code.add_command("je", label)
        asm_code.add_command("mov", output_asm, self.not_equal_value)
        asm_code.add_label(label)


class NotEqualCmp(_GeneralEqualCmp):
    """NotEqualCmp - checks whether arg1 and arg2 are not equal.

    IL value output must have int type. arg1, arg2 must all have the same
    type. No type conversion or promotion is done here.

    """

    equal_value = "0"
    not_equal_value = "1"

    def __str__(self):  # pragma: no cover
        return self.to_str("NEQ", [self.arg1, self.arg2], self.output)


class EqualCmp(_GeneralEqualCmp):
    """EqualCmp - checks whether arg1 and arg2 are equal.

    IL value output must have int type. arg1, arg2 must all have the same
    type. No type conversion or promotion is done here.

    """

    equal_value = "1"
    not_equal_value = "0"

    def __str__(self):  # pragma: no cover
        return self.to_str("NEQ", [self.arg1, self.arg2], self.output)


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
            moves = {}
            output_asm = spotmap[self.output].asm_str(self.output.ctype.size)
            arg_asm = spotmap[self.arg].asm_str(self.arg.ctype.size)
            asm_code.add_command("mov", output_asm, arg_asm)
        elif self.output.ctype.size <= self.arg.ctype.size:
            moves = {}
            if spotmap[self.output] == spotmap[self.arg]:
                return moves

            small_arg_asm = spotmap[self.arg].asm_str(self.output.ctype.size)
            output_asm = spotmap[self.output].asm_str(self.output.ctype.size)

            # TODO: In some cases, an extra mov may be emitted.
            # get_reg returns a FREE register. so, even if self.arg is in a
            # register, if it's not free, that register will not be returned.
            r = get_reg([spotmap[self.output], spotmap[self.arg]])
            r_asm = r.asm_str(self.output.ctype.size)

            if r != spotmap[self.arg]:
                asm_code.add_command("mov", r_asm, small_arg_asm)
                if self.output.ctype.size == self.arg.ctype.size:
                    moves[self.arg] = [r]

            if spotmap[self.output] != r:
                asm_code.add_command("mov", output_asm, r_asm)
                moves[self.output] = [r]
        else:
            moves = {}
            arg_asm = spotmap[self.arg].asm_str(self.arg.ctype.size)
            output_asm = spotmap[self.output].asm_str(self.output.ctype.size)

            r = get_reg([spotmap[self.output], spotmap[self.arg]])
            r_asm = r.asm_str(self.output.ctype.size)

            # Move from arg_asm -> r_asm
            if self.arg.ctype.signed:
                asm_code.add_command("movsx", r_asm, arg_asm)
            elif self.arg.ctype.size == 4:
                small_r_asm = r.asm_str(4)
                asm_code.add_command("mov", small_r_asm, arg_asm)
            else:
                asm_code.add_command("movzx", r_asm, arg_asm)

            # If necessary, move from r_asm -> output_asm
            if r != spotmap[self.output]:
                moves[self.output] = r
                asm_code.add_command("mov", output_asm, r_asm)

        return moves

    def _set_bool(self, spotmap, get_reg, asm_code):
        """Emit code for SET command if arg is boolean type."""
        # When any scalar value is converted to _Bool, the result is 0 if the
        # value compares equal to 0; otherwise, the result is 1

        arg_asm_old = spotmap[self.arg].asm_str(self.arg.ctype.size)

        # If arg_asm is a LITERAL, move to register.
        if spotmap[self.arg].spot_type == Spot.LITERAL:
            r = get_reg()
            r_asm = r.asm_str(self.arg.ctype.size)
            asm_code.add_command("mov", r_asm, arg_asm_old)
            arg_asm = r_asm
        else:
            arg_asm = arg_asm_old

        label = asm_code.get_label()
        output_asm = spotmap[self.output].asm_str(self.output.ctype.size)
        asm_code.add_command("mov", output_asm, "0")
        asm_code.add_command("cmp", arg_asm, "0")
        asm_code.add_command("je", label)
        asm_code.add_command("mov", output_asm, "1")
        asm_code.add_label(label)

    def __str__(self):  # pragma: no cover
        return self.to_str("SET", [self.arg], self.output)


class Return(ILCommand):
    """RETURN - returns the given value from function.

    For now, arg must have type int.

    """

    def __init__(self, arg): # noqa D102
        # arg must already be cast to return type
        self.arg = arg

    def inputs(self): # noqa D102
        return [self.arg]

    def outputs(self): # noqa D102
        return []

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        arg_asm = spotmap[self.arg].asm_str(self.arg.ctype.size)
        rax_asm = spots.RAX.asm_str(self.arg.ctype.size)

        asm_code.add_command("mov", rax_asm, arg_asm)
        asm_code.add_command("mov", "rsp", "rbp")
        asm_code.add_command("pop", "rbp")
        asm_code.add_command("ret")

    def __str__(self):  # pragma: no cover
        return self.to_str("RET", [self.arg])


class Label(ILCommand):
    """Label - Analogous to an ASM label."""

    def __init__(self, label): # noqa D102
        """The label argument is an string label name unique to this label."""
        self.label = label

    def inputs(self): # noqa D102
        return []

    def outputs(self): # noqa D102
        return []

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        asm_code.add_label(self.label)

    def __str__(self):  # pragma: no cover
        return self.to_str("LABEL", [self.label])


class JumpZero(ILCommand):
    """Jumps to a label if given condition is zero."""

    def __init__(self, cond, label): # noqa D102
        self.cond = cond
        self.label = label

    def inputs(self): # noqa D102
        return [self.cond]

    def outputs(self): # noqa D102
        return []

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        if spotmap[self.cond].spot_type == Spot.LITERAL:
            cond_asm_old = spotmap[self.cond].asm_str(self.cond.ctype.size)
            rax_asm = spots.RAX.asm_str(self.cond.ctype.size)
            asm_code.add_command("mov", rax_asm, cond_asm_old)
            cond_asm = rax_asm
        else:
            cond_asm = spotmap[self.cond].asm_str(self.cond.ctype.size)

        asm_code.add_command("cmp", cond_asm, "0")
        asm_code.add_command("je", self.label)

    def __str__(self):  # pragma: no cover
        return self.to_str("JZERO", [self.cond, self.label])


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

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        # TODO: Use permanent spot of var, not spotmap temporary spot
        var_asm = spotmap[self.var].asm_str(0)
        temp = spots.RAX.asm_str(self.output.ctype.size)
        output_asm = spotmap[self.output].asm_str(self.output.ctype.size)

        asm_code.add_command("lea", temp, var_asm)
        asm_code.add_command("mov", output_asm, temp)

    def __str__(self):  # pragma: no cover
        return self.to_str("ADDROF", [self.var], self.output)


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

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        addr_asm = spotmap[self.addr].asm_str(8)
        rax = spots.RAX.asm_str(8)
        temp = spots.RAX.asm_str(self.output.ctype.size)
        rax_spot = Spot(Spot.MEM, ("rax", 0)).asm_str(self.output.ctype.size)
        output_asm = spotmap[self.output].asm_str(self.output.ctype.size)

        asm_code.add_command("mov", rax, addr_asm)
        asm_code.add_command("mov", temp, rax_spot)
        asm_code.add_command("mov", output_asm, temp)

    def __str__(self):  # pragma: no cover
        return self.to_str("READAT", [self.addr], self.output)


class Call(ILCommand):
    """Call a given function.

    func - Name of the function to call as a function IL value
    args - Arguments of the function, in left-to-right order. Must match the
    parameter types the function expects.
    ret - IL value to save the return value. Must match the function return
    value.

    """

    def __init__(self, func, args, ret): # noqa D102
        self.func = func
        self.args = args
        self.ret = ret

    def inputs(self): # noqa D102
        return [self.func] + self.args

    def outputs(self): # noqa D102
        return [self.ret]

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        # Registers ordered from first to last for arguments.
        regs = [spots.RDI, spots.RSI, spots.RDX]

        # Reverse the registers to go from last to first, so we can pop() out
        # registers.
        regs.reverse()
        for arg in self.args:
            if arg.ctype.type_type != CType.ARITH:
                raise NotImplementedError("only integer arguments supported")
            elif not regs:
                raise NotImplementedError("too many arguments")

            reg = regs.pop()
            asm_code.add_command("mov", reg.asm_str(arg.ctype.size),
                                 spotmap[arg].asm_str(arg.ctype.size))

        # TODO: Fix this hack! Once pointers are implemented there will
        # hopefully be a better way to call functions.
        asm_code.add_command("call", spotmap[self.func].detail)

        ret_asm = spotmap[self.ret].asm_str(self.func.ctype.ret.size)
        rax_asm = spots.RAX.asm_str(self.func.ctype.ret.size)
        asm_code.add_command("mov", ret_asm, rax_asm)

    def __str__(self):  # pragma: no cover
        return self.to_str("CALL", self.args, self.ret)
