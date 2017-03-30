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

    def rel_spot_conf(self):
        """Return the relative conflict list of this command.

        This function returns a dictionary mapping an ILValue to a list of
        ILValues. If this contains a key value pair k: [t1, t2], then the
        register allocator will attempt to place ILValue k in a different spot
        than t1 and t2. It is assumed by default that the inputs do
        not share the same spot.
        """
        return {}

    def abs_spot_conf(self):
        """Return the absolute conflict list of this command.

        This function returns a dictionary mapping an ILValue to a list of
        spots. If this contains a key value pair k: [s1, s2], then the
        register allocator will attempt to place ILValue k in a spot which
        is not s1 or s2.
        """
        return {}

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

    def label_name(self):
        """If this command is a label, return its name."""
        return None

    def targets(self):
        """Return list of any labels to which this command may jump."""
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
        """
        raise NotImplementedError

    def _assert_same_ctype(self, il_values):
        """Raise ValueError if all IL values do not have the same type."""
        ctype = None
        for il_value in il_values:
            if ctype and ctype != il_value.ctype:
                raise ValueError("different ctypes")  # pragma: no cover

    def _is_imm(self, spot):
        """Return True iff given spot is an immediate operand."""
        return spot.spot_type == Spot.LITERAL

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


class _AddMult(ILCommand):
    """Base class for ADD and MULT.

    Contains function that implements the shared code between these.
    """

    def _shared_asm(self, inst, out, arg1, arg2, spotmap, get_reg, asm_code):
        """Make the shared ASM for ADD and MULT.

        inst (str) - the instruction, for ADD it is "add" and for MULT it is
        "imul"
        """
        ctype = arg1.ctype
        output_asm = spotmap[out].asm_str(ctype.size)
        arg1_asm = spotmap[arg1].asm_str(ctype.size)
        arg2_asm = spotmap[arg2].asm_str(ctype.size)

        # Get temp register for computation.
        temp = get_reg([spotmap[out],
                        spotmap[arg1],
                        spotmap[arg2]])
        temp_asm = temp.asm_str(ctype.size)

        if temp == spotmap[arg1]:
            if not self._is_imm64(spotmap[arg2]):
                asm_code.add_command(inst, temp_asm, arg2_asm)
            else:
                temp2 = get_reg([], [temp])
                temp2_asm = temp2.asm_str(ctype.size)
                asm_code.add_command("mov", temp2_asm, arg2_asm)
                asm_code.add_command(inst, temp_asm, temp2_asm)
        elif temp == spotmap[arg2]:
            if not self._is_imm64(spotmap[arg1]):
                asm_code.add_command(inst, temp_asm, arg1_asm)
            else:
                temp2 = get_reg([], [temp])
                temp2_asm = temp2.asm_str(ctype.size)
                asm_code.add_command("mov", temp2_asm, arg1_asm)
                asm_code.add_command(inst, temp_asm, temp2_asm)
        else:
            if (not self._is_imm64(spotmap[arg1]) and
                 not self._is_imm64(spotmap[arg2])):
                asm_code.add_command("mov", temp_asm, arg1_asm)
                asm_code.add_command(inst, temp_asm, arg2_asm)
            elif (self._is_imm64(spotmap[arg1]) and
                  not self._is_imm64(spotmap[arg2])):
                asm_code.add_command("mov", temp_asm, arg1_asm)
                asm_code.add_command(inst, temp_asm, arg2_asm)
            elif (not self._is_imm64(spotmap[arg1]) and
                  self._is_imm64(spotmap[arg2])):
                asm_code.add_command("mov", temp_asm, arg2_asm)
                asm_code.add_command(inst, temp_asm, arg1_asm)
            else:  # both are imm64
                temp2 = get_reg([], [temp])
                temp2_asm = temp2.asm_str(ctype.size)
                asm_code.add_command("mov", temp_asm, arg1_asm)
                asm_code.add_command("mov", temp2_asm, arg2_asm)
                asm_code.add_command(inst, temp_asm, temp2_asm)

        if temp != spotmap[out]:
            asm_code.add_command("mov", output_asm, temp_asm)


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
        self._shared_asm("add", self.output, self.arg1, self.arg2,
                         spotmap, get_reg, asm_code)

    def __str__(self):    # pragma: no cover
        return self.to_str("ADD", [self.arg1, self.arg2], self.output)


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
        output_asm = spotmap[self.output].asm_str(ctype.size)
        arg1_asm = spotmap[self.arg1].asm_str(ctype.size)
        arg2_asm = spotmap[self.arg2].asm_str(ctype.size)

        # Unsigned multiplication
        if not ctype.signed:
            rax_asm = spots.RAX.asm_str(ctype.size)

            if spotmap[self.arg1] == spots.RAX:
                mul_spot = spotmap[self.arg2]
            elif spotmap[self.arg2] == spots.RAX:
                mul_spot = spotmap[self.arg1]
            else:
                # If either is literal, move that one to RAX
                if self._is_imm(spotmap[self.arg2]):
                    asm_code.add_command("mov", rax_asm, arg2_asm)
                    mul_spot = spotmap[self.arg1]
                else:
                    asm_code.add_command("mov", rax_asm, arg1_asm)
                    mul_spot = spotmap[self.arg2]

            # Operand is an immediate, move it to a register
            if self._is_imm(mul_spot):
                r = get_reg([], [spots.RAX])
                asm_code.add_command("mov", r.asm_str(ctype.size),
                                     mul_spot.asm_str(ctype.size))
                mul_spot = r

            asm_code.add_command("mul", mul_spot.asm_str(ctype.size))

            if spotmap[self.output] != spots.RAX:
                asm_code.add_command("mov", output_asm, rax_asm)

        # Signed multiplication
        else:
            self._shared_asm("imul", self.output, self.arg1, self.arg2,
                             spotmap, get_reg, asm_code)

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

    def clobber(self): # noqa D102
        return [spots.RAX, spots.RDX]

    def abs_spot_pref(self): # noqa D102
        return {self.output: [spots.RAX],
                self.arg1: [spots.RAX]}

    def abs_spot_conf(self): # noqa D102
        return {self.arg2: [spots.RDX, spots.RAX]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        ctype = self.arg1.ctype
        output_asm = spotmap[self.output].asm_str(ctype.size)
        arg1_asm = spotmap[self.arg1].asm_str(ctype.size)
        arg2_asm = spotmap[self.arg2].asm_str(ctype.size)

        rax_asm = spots.RAX.asm_str(ctype.size)
        rdx_asm = spots.RDX.asm_str(ctype.size)

        # Move first operand into RAX if we can do so without clobbering
        # other argument
        moved_to_rax = False
        if spotmap[self.arg1] != spots.RAX and spotmap[self.arg2] != spots.RAX:
            moved_to_rax = True
            asm_code.add_command("mov", rax_asm, arg1_asm)

        # If the divisor is a literal or in a bad register, we must move it
        # to a register.
        if (self._is_imm(spotmap[self.arg2]) or
             spotmap[self.arg2] in [spots.RAX, spots.RDX]):
            r = get_reg([], [spots.RAX, spots.RDX])
            r_asm = r.asm_str(ctype.size)
            asm_code.add_command("mov", r_asm, arg2_asm)
            arg2_final_asm = r_asm
        else:
            arg2_final_asm = arg2_asm

        # If we did not move to RAX above, do so here.
        if not moved_to_rax and spotmap[self.arg1] != spots.RAX:
            asm_code.add_command("mov", rax_asm, arg1_asm)

        if ctype.signed:
            if ctype.size == 4:
                asm_code.add_command("cdq")  # sign extend EAX into EDX
            elif ctype.size == 8:
                asm_code.add_command("cqo")  # sign extend RAX into RDX
            asm_code.add_command("idiv", arg2_final_asm)
        else:
            # zero out RDX register
            asm_code.add_command("xor", rdx_asm, rdx_asm)
            asm_code.add_command("div", arg2_final_asm)

        if spotmap[self.output] != spots.RAX:
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

    def rel_spot_conf(self):  # noqa D102
        return {self.output: [self.arg1, self.arg2]}

    def _fix_both_literal_or_mem(self, arg1_spot, arg2_spot, regs,
                                 get_reg, asm_code):
        """Fix arguments if both are literal or memory.

        Adds any called registers to given regs list. Returns tuple where
        first element is new spot of arg1 and second element is new spot of
        arg2.
        """
        if ((arg1_spot.spot_type == Spot.LITERAL and
             arg2_spot.spot_type == Spot.LITERAL) or
            (arg1_spot.spot_type == Spot.MEM and
             arg2_spot.spot_type == Spot.MEM)):

            # No need to worry about r overlapping with arg1 or arg2 because
            # in this case both are literal/memory.
            r = get_reg([], regs)
            regs.append(r)
            asm_code.add_command("mov", r.asm_str(self.arg1.ctype.size),
                                 arg1_spot.asm_str(self.arg1.ctype.size))
            return r, arg2_spot
        else:
            return arg1_spot, arg2_spot

    def _fix_either_literal64(self, arg1_spot, arg2_spot, regs,
                              get_reg, asm_code):
        """Move any 64-bit immediate operands to register."""

        if self._is_imm64(arg1_spot):
            new_arg1_spot = get_reg([], regs + [arg2_spot])
            new_arg1_spot_asm = new_arg1_spot.asm_str(self.arg1.ctype.size)
            old_arg1_spot_asm = arg1_spot.asm_str(self.arg1.ctype.size)
            asm_code.add_command("mov", new_arg1_spot_asm, old_arg1_spot_asm)
            return new_arg1_spot, arg2_spot

        # We cannot have both cases because _fix_both_literal is called
        # before this.
        elif self._is_imm64(arg2_spot):
            new_arg2_spot = get_reg([], regs + [arg1_spot])
            new_arg2_spot_asm = new_arg2_spot.asm_str(self.arg2.ctype.size)
            old_arg2_spot_asm = arg2_spot.asm_str(self.arg2.ctype.size)
            asm_code.add_command("mov", new_arg2_spot_asm, old_arg2_spot_asm)
            return arg1_spot, new_arg2_spot

        else:
            return arg1_spot, arg2_spot


    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        output_asm = spotmap[self.output].asm_str(self.output.ctype.size)

        regs = []

        result = get_reg([spotmap[self.output]],
                         [spotmap[self.arg1], spotmap[self.arg2]])
        result_asm = result.asm_str(self.output.ctype.size)
        regs.append(result)

        asm_code.add_command("mov", result_asm, self.equal_value)

        arg1_spot, arg2_spot = self._fix_both_literal_or_mem(
            spotmap[self.arg1], spotmap[self.arg2], regs, get_reg, asm_code)
        arg1_spot, arg2_spot = self._fix_either_literal64(
            arg1_spot, arg2_spot, regs, get_reg, asm_code)

        arg1_asm = arg1_spot.asm_str(self.arg1.ctype.size)
        arg2_asm = arg2_spot.asm_str(self.arg2.ctype.size)

        label = asm_code.get_label()
        asm_code.add_command("cmp", arg1_asm, arg2_asm)
        asm_code.add_command("je", label)
        asm_code.add_command("mov", result_asm, self.not_equal_value)
        asm_code.add_label(label)

        if result != spotmap[self.output]:
            asm_code.add_command("mov", output_asm, result_asm)


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

            if spotmap[self.output].spot_type == Spot.REGISTER:
                r = spotmap[self.output]
            elif spotmap[self.arg].spot_type == Spot.REGISTER:
                r = spotmap[self.arg]
            else:
                r = get_reg()
            r_asm = r.asm_str(self.output.ctype.size)

            if r != spotmap[self.arg]:
                asm_code.add_command("mov", r_asm, small_arg_asm)
                if self.output.ctype.size == self.arg.ctype.size:
                    moves[self.arg] = [r]

            if r != spotmap[self.output]:
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
            r = get_reg([], [spotmap[self.output]])
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

    def clobber(self):  # noqa D102
        return [spots.RAX]

    def abs_spot_pref(self):  # noqa D102
        return {self.arg: [spots.RAX]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        arg_asm = spotmap[self.arg].asm_str(self.arg.ctype.size)
        rax_asm = spots.RAX.asm_str(self.arg.ctype.size)

        if spotmap[self.arg] != spots.RAX:
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

    def label_name(self):  # noqa D102
        return self.label

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

    def targets(self): # noqa D102
        return [self.label]

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        if spotmap[self.cond].spot_type == Spot.LITERAL:
            cond_asm_old = spotmap[self.cond].asm_str(self.cond.ctype.size)
            r_asm = get_reg().asm_str(self.cond.ctype.size)
            asm_code.add_command("mov", r_asm, cond_asm_old)
            cond_asm = r_asm
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

    def references(self):  # noqa D102
        return {self.output: [self.var]}

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        var_asm = home_spots[self.var].asm_str(0)

        r = get_reg([spotmap[self.output]])
        r_asm = r.asm_str(self.output.ctype.size)
        asm_code.add_command("lea", r_asm, var_asm)

        if r != spotmap[self.output]:
            output_asm = spotmap[self.output].asm_str(self.output.ctype.size)
            asm_code.add_command("mov", output_asm, r_asm)

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

    def indir_read(self):  # noqa D102
        return [self.addr]

    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        addr_asm = spotmap[self.addr].asm_str(8)
        output_asm = spotmap[self.output].asm_str(self.output.ctype.size)

        if spotmap[self.addr].spot_type == Spot.REGISTER:
            indir_spot = Spot(Spot.MEM, (spotmap[self.addr].asm_str(8), 0))
        else:
            r = get_reg()
            asm_code.add_command("mov", r.asm_str(8), addr_asm)
            indir_spot = Spot(Spot.MEM, (r.asm_str(8), 0))

        indir_asm = indir_spot.asm_str(self.output.ctype.size)
        asm_code.add_command("mov", output_asm, indir_asm)

    def __str__(self):  # pragma: no cover
        return self.to_str("READAT", [self.addr], self.output)


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
        addr_asm = spotmap[self.addr].asm_str(8)
        val_asm = spotmap[self.val].asm_str(self.val.ctype.size)

        if spotmap[self.addr].spot_type == Spot.REGISTER:
            indir_spot = Spot(Spot.MEM, (spotmap[self.addr].asm_str(8), 0))
        else:
            r = get_reg()
            asm_code.add_command("mov", r.asm_str(8), addr_asm)
            indir_spot = Spot(Spot.MEM, (r.asm_str(8), 0))

        indir_asm = indir_spot.asm_str(self.val.ctype.size)
        asm_code.add_command("mov", indir_asm, val_asm)


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
