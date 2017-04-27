"""Classes representing IL commands.

Each IL command is represented by a class that inherits from the ILCommand
interface. The implementation provides code that generates ASM for each IL
command.

For arithmetic commands like Add or Mult, the arguments and output must all be
pre-cast to the same type. In addition, this type must be size `int` or greater
per the C spec. The Set command is exempt from this requirement, and can be
used to cast.

"""

import asm_cmd
import ctypes
import spots
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
                asm_code.add(asm_cmd.Mov(temp2, arg2_spot, size))
                asm_code.add(Inst(temp, temp2, size))
        elif temp == arg2_spot:
            if not self._is_imm64(arg1_spot):
                asm_code.add(Inst(temp, arg1_spot, size))
            else:
                temp2 = get_reg([], [temp])
                asm_code.add(asm_cmd.Mov(temp2, arg1_spot, size))
                asm_code.add(Inst(temp, temp2, size))

            if not comm:
                asm_code.add(asm_cmd.Neg(temp, None, size))

        else:
            if (not self._is_imm64(arg1_spot) and
                 not self._is_imm64(arg2_spot)):
                asm_code.add(asm_cmd.Mov(temp, arg1_spot, size))
                asm_code.add(Inst(temp, arg2_spot, size))
            elif (self._is_imm64(arg1_spot) and
                  not self._is_imm64(arg2_spot)):
                asm_code.add(asm_cmd.Mov(temp, arg1_spot, size))
                asm_code.add(Inst(temp, arg2_spot, size))
            elif (not self._is_imm64(arg1_spot) and
                  self._is_imm64(arg2_spot)):
                asm_code.add(asm_cmd.Mov(temp, arg2_spot, size))
                asm_code.add(Inst(temp, arg1_spot, size))
                if not comm:
                    asm_code.add(asm_cmd.Neg(temp, None, size))

            else:  # both are imm64
                temp2 = get_reg([], [temp])

                asm_code.add(asm_cmd.Mov(temp, arg1_spot, size))
                asm_code.add(asm_cmd.Mov(temp2, arg2_spot, size))
                asm_code.add(Inst(temp, temp2, size))

        if temp != spotmap[out]:
            asm_code.add(asm_cmd.Mov(spotmap[out], temp, size))


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
        self._shared_asm(asm_cmd.Add, True, self.output, self.arg1, self.arg2,
                         spotmap, get_reg, asm_code)

    def __str__(self):    # pragma: no cover
        return self.to_str("ADD", [self.arg1, self.arg2], self.output)


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
        self._shared_asm(asm_cmd.Sub, False, self.out, self.arg1, self.arg2,
                         spotmap, get_reg, asm_code)

    def __str__(self):    # pragma: no cover
        return self.to_str("SUBTR", [self.arg1, self.arg2], self.out)


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
                    asm_code.add(asm_cmd.Mov(spots.RAX, arg2_spot, size))
                    mul_spot = arg1_spot
                else:
                    asm_code.add(asm_cmd.Mov(spots.RAX, arg1_spot, size))
                    mul_spot = arg2_spot

            # Operand is an immediate, move it to a register
            if self._is_imm(mul_spot):
                r = get_reg([], [spots.RAX])
                asm_code.add(asm_cmd.Mov(r, mul_spot, ctype.size))
                mul_spot = r

            asm_code.add(asm_cmd.Mul(mul_spot, None, ctype.size))

            if spotmap[self.output] != spots.RAX:
                asm_code.add(
                    asm_cmd.Mov(spotmap[self.output], spots.RAX, ctype.size))

        # Signed multiplication
        else:
            self._shared_asm(asm_cmd.Imul, True, self.output, self.arg1,
                             self.arg2, spotmap, get_reg, asm_code)

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
        size = ctype.size

        output_spot = spotmap[self.output]
        arg1_spot = spotmap[self.arg1]
        arg2_spot = spotmap[self.arg2]

        # Move first operand into RAX if we can do so without clobbering
        # other argument
        moved_to_rax = False
        if spotmap[self.arg1] != spots.RAX and spotmap[self.arg2] != spots.RAX:
            moved_to_rax = True
            asm_code.add(asm_cmd.Mov(spots.RAX, arg1_spot, size))

        # If the divisor is a literal or in a bad register, we must move it
        # to a register.
        if (self._is_imm(spotmap[self.arg2]) or
             spotmap[self.arg2] in [spots.RAX, spots.RDX]):
            r = get_reg([], [spots.RAX, spots.RDX])
            asm_code.add(asm_cmd.Mov(r, arg2_spot, size))
            arg2_final_spot = r
        else:
            arg2_final_spot = arg2_spot

        # If we did not move to RAX above, do so here.
        if not moved_to_rax and arg1_spot != spots.RAX:
            asm_code.add(asm_cmd.Mov(spots.RAX, arg1_spot, size))

        if ctype.signed:
            if ctype.size == 4:
                asm_code.add(asm_cmd.Cdq())
            elif ctype.size == 8:
                asm_code.add(asm_cmd.Cqo())
            asm_code.add(asm_cmd.Idiv(arg2_final_spot, None, size))
        else:
            # zero out RDX register
            asm_code.add(asm_cmd.Xor(spots.RDX, spots.RDX, size))
            asm_code.add(asm_cmd.Div(arg2_final_spot, None, size))

        if spotmap[self.output] != spots.RAX:
            asm_code.add(asm_cmd.Mov(output_spot, spots.RAX, size))

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
            asm_code.add(asm_cmd.Mov(r, arg1_spot, self.arg1.ctype.size))
            return r, arg2_spot
        else:
            return arg1_spot, arg2_spot

    def _fix_either_literal64(self, arg1_spot, arg2_spot, regs,
                              get_reg, asm_code):
        """Move any 64-bit immediate operands to register."""

        if self._is_imm64(arg1_spot):
            size = self.arg1.ctype.size
            new_arg1_spot = get_reg([], regs + [arg2_spot])
            asm_code.add(asm_cmd.Mov(new_arg1_spot, arg1_spot, size))
            return new_arg1_spot, arg2_spot

        # We cannot have both cases because _fix_both_literal is called
        # before this.
        elif self._is_imm64(arg2_spot):
            size = self.arg2.ctype.size
            new_arg2_spot = get_reg([], regs + [arg1_spot])
            asm_code.add(asm_cmd.Mov(new_arg2_spot, arg2_spot, size))
            return arg1_spot, new_arg2_spot
        else:
            return arg1_spot, arg2_spot


    def make_asm(self, spotmap, home_spots, get_reg, asm_code):  # noqa D102
        regs = []

        result = get_reg([spotmap[self.output]],
                         [spotmap[self.arg1], spotmap[self.arg2]])
        regs.append(result)

        out_size = self.output.ctype.size
        eq_val_spot = Spot(Spot.LITERAL, self.equal_value)
        asm_code.add(asm_cmd.Mov(result, eq_val_spot, out_size))

        arg1_spot, arg2_spot = self._fix_both_literal_or_mem(
            spotmap[self.arg1], spotmap[self.arg2], regs, get_reg, asm_code)
        arg1_spot, arg2_spot = self._fix_either_literal64(
            arg1_spot, arg2_spot, regs, get_reg, asm_code)

        arg_size = self.arg1.ctype.size
        neq_val_spot = Spot(Spot.LITERAL, self.not_equal_value)
        label = asm_code.get_label()

        asm_code.add(asm_cmd.Cmp(arg1_spot, arg2_spot, arg_size))
        asm_code.add(asm_cmd.Je(label))
        asm_code.add(asm_cmd.Mov(result, neq_val_spot, out_size))
        asm_code.add(asm_cmd.Label(label))

        if result != spotmap[self.output]:
            asm_code.add(asm_cmd.Mov(spotmap[self.output], result, out_size))


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
            out_spot = spotmap[self.output]
            arg_spot = spotmap[self.arg]
            size = self.output.ctype.size
            asm_code.add(asm_cmd.Mov(out_spot, arg_spot, size))
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
                asm_code.add(asm_cmd.Mov(r, spotmap[self.arg], size))

            if r != spotmap[self.output]:
                asm_code.add(asm_cmd.Mov(output_spot, r, size))

        else:
            r = get_reg([spotmap[self.output], spotmap[self.arg]])

            # Move from arg_asm -> r_asm
            if self.arg.ctype.signed:
                asm_code.add(asm_cmd.Movsx(r, spotmap[self.arg],
                                           self.output.ctype.size,
                                           self.arg.ctype.size))
            elif self.arg.ctype.size == 4:
                asm_code.add(asm_cmd.Mov(r, spotmap[self.arg], 4))
            else:
                asm_code.add(asm_cmd.Movzx(r, spotmap[self.arg],
                                           self.output.ctype.size,
                                           self.arg.ctype.size))

            # If necessary, move from r_asm -> output_asm
            if r != spotmap[self.output]:
                asm_code.add(asm_cmd.Mov(spotmap[self.output],
                                         r, self.output.ctype.size))

    def _set_bool(self, spotmap, get_reg, asm_code):
        """Emit code for SET command if arg is boolean type."""
        # When any scalar value is converted to _Bool, the result is 0 if the
        # value compares equal to 0; otherwise, the result is 1

        # If arg_asm is a LITERAL, move to register.
        if spotmap[self.arg].spot_type == Spot.LITERAL:
            r = get_reg([], [spotmap[self.output]])
            asm_code.add(
                asm_cmd.Mov(r, spotmap[self.arg], self.arg.ctype.size))
            arg_spot = r
        else:
            arg_spot = spotmap[self.arg]

        label = asm_code.get_label()
        output_spot = spotmap[self.output]

        zero = Spot(Spot.LITERAL, "0")
        one = Spot(Spot.LITERAL, "1")

        asm_code.add(asm_cmd.Mov(output_spot, zero, self.output.ctype.size))
        asm_code.add(asm_cmd.Cmp(arg_spot, zero, self.arg.ctype.size))
        asm_code.add(asm_cmd.Je(label))
        asm_code.add(asm_cmd.Mov(output_spot, one, self.output.ctype.size))
        asm_code.add(asm_cmd.Label(label))

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
        if spotmap[self.arg] != spots.RAX:
            size = self.arg.ctype.size
            asm_code.add(asm_cmd.Mov(spots.RAX, spotmap[self.arg], size))

        asm_code.add(asm_cmd.Mov(spots.RSP, spots.RBP, 8))
        asm_code.add(asm_cmd.Pop(spots.RBP, None, 8))
        asm_code.add(asm_cmd.Ret())

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
        asm_code.add(asm_cmd.Label(self.label))

    def __str__(self):  # pragma: no cover
        return self.to_str("LABEL", [self.label])


class Jump(ILCommand):
    """Jumps unconditionally to a label."""

    def __init__(self, label): # noqa D102
        self.label = label

    def inputs(self): # noqa D102
        return []

    def outputs(self): # noqa D102
        return []

    def targets(self): # noqa D102
        return [self.label]

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        asm_code.add(asm_cmd.Jmp(self.label))

    def __str__(self):  # pragma: no cover
        return self.to_str("JMP", [self.label])


class _GeneralJumpZero(ILCommand):
    """General class for jumping to a label based on condition."""

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
        size = self.cond.ctype.size

        if spotmap[self.cond].spot_type == Spot.LITERAL:
            r = get_reg()
            asm_code.add(asm_cmd.Mov(r, spotmap[self.cond], size))
            cond_spot = r
        else:
            cond_spot = spotmap[self.cond]

        zero_spot = Spot(Spot.LITERAL, "0")
        asm_code.add(asm_cmd.Cmp(cond_spot, zero_spot, size))
        asm_code.add(self.command(self.label))


class JumpZero(_GeneralJumpZero):
    """Jumps to a label if given condition is zero."""

    command = asm_cmd.Je

    def __str__(self):  # pragma: no cover
        return self.to_str("JZERO", [self.cond, self.label])


class JumpNotZero(_GeneralJumpZero):
    """Jumps to a label if given condition is zero."""

    command = asm_cmd.Jne

    def __str__(self):  # pragma: no cover
        return self.to_str("JNZERO", [self.cond, self.label])


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
        asm_code.add(asm_cmd.Lea(r, home_spots[self.var]))

        if r != spotmap[self.output]:
            size = self.output.ctype.size
            asm_code.add(asm_cmd.Mov(spotmap[self.output], r, size))

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
        addr_spot = spotmap[self.addr]
        output_spot = spotmap[self.output]

        if spotmap[self.addr].spot_type == Spot.REGISTER:
            indir_spot = Spot(Spot.MEM, (spotmap[self.addr], 0))
        else:
            r = get_reg()
            asm_code.add(asm_cmd.Mov(r, addr_spot, 8))
            indir_spot = Spot(Spot.MEM, (r, 0))

        size = self.output.ctype.size
        asm_code.add(asm_cmd.Mov(output_spot, indir_spot, size))

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
        size = self.val.ctype.size
        if spotmap[self.addr].spot_type == Spot.REGISTER:
            indir_spot = Spot(Spot.MEM, (spotmap[self.addr], 0))
        else:
            r = get_reg([], [spotmap[self.val]])
            asm_code.add(asm_cmd.Mov(r, spotmap[self.addr], 8))
            indir_spot = Spot(Spot.MEM, (r, 0))

        asm_code.add(
            asm_cmd.Mov(indir_spot, spotmap[self.val], size))


class Call(ILCommand):
    """Call a given function.

    func - Pointer to function
    args - Arguments of the function, in left-to-right order. Must match the
    parameter types the function expects.
    ret - If function has non-void return type, IL value to save the return
    value. Its type must match the function return value.
    """

    arg_regs = [spots.RDI, spots.RSI, spots.RDX, spots.RCX, spots.R8, spots.R9]

    def __init__(self, func, args, ret): # noqa D102
        self.func = func
        self.args = args
        self.ret = ret
        self.void_return = self.func.ctype.arg.ret.is_void()

        if len(self.args) > len(self.arg_regs):
            raise NotImplementedError("too many arguments")

    def inputs(self): # noqa D102
        return [self.func] + self.args

    def outputs(self): # noqa D102
        return [] if self.void_return else [self.ret]

    def clobber(self): # noqa D102
        # All caller-saved registers are clobbered by function call
        return [spots.RAX, spots.RCX, spots.RDX, spots.RSI, spots.RDI,
                spots.R8, spots.R9, spots.R10, spots.R11]

    def abs_spot_pref(self): # noqa D102
        prefs = {} if self.void_return else {self.ret: [spots.RAX]}
        for arg, reg in zip(self.args, self.arg_regs):
            prefs[arg] = [reg]

        return prefs

    def abs_spot_conf(self): # noqa D102
        # We don't want the function pointer to be in the same register as
        # an argument will be placed into.
        return {self.func: self.arg_regs[0:len(self.args)]}

    def indir_write(self): # noqa D102
        return self.args

    def indir_read(self): # noqa D102
        return self.args

    def make_asm(self, spotmap, home_spots, get_reg, asm_code): # noqa D102
        func_spot = spotmap[self.func]

        func_size = self.func.ctype.size
        ret_size = self.func.ctype.arg.ret.size

        # Check if function pointer spot will be clobbered by moving the
        # arguments into the correct registers.
        if spotmap[self.func] in self.arg_regs[0:len(self.args)]:
            # Get a register which isn't one of the unallowed registers.
            r = get_reg([], self.arg_regs[0:len(self.args)])
            asm_code.add(asm_cmd.Mov(r, spotmap[self.func], func_size))
            func_spot = r

        for arg, reg in zip(self.args, self.arg_regs):
            if spotmap[arg] == reg:
                continue
            asm_code.add(asm_cmd.Mov(reg, spotmap[arg], arg.ctype.size))

        asm_code.add(asm_cmd.Call(func_spot, None, self.func.ctype.size))

        if not self.void_return and spotmap[self.ret] != spots.RAX:
            asm_code.add(asm_cmd.Mov(self.ret, spots.RAX, ret_size))

    def __str__(self):  # pragma: no cover
        return self.to_str("CALL", self.args, self.ret)
