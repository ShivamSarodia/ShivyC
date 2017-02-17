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
from asm_gen import ASMCode
from spots import Spot


class ILCommand:
    """Base interface for all IL commands."""

    def input_values(self):
        """Return list of values read by this command."""
        raise NotImplementedError

    def output_values(self):
        """Return list of values modified by this command."""
        raise NotImplementedError

    def clobber_spots(self):
        """Return list of spots that are clobbered by this command."""
        raise NotImplementedError

    def make_asm(self, spotmap, asm_code):
        """Generate assembly code for this command.

        Generated assembly can read any of the values returned from
        input_values, may overwrite any values returned from output_values, and
        may change the value of any spots returned from clobber_spots.

        asm_code (ASMCode) - Object to which to save generated code.
        spotmap - Dictionary mapping each input/output value to a spot.

        """
        raise NotImplementedError

    def __eq__(self, other):
        """Check equality by comparing types."""
        return type(other) == type(self)

    def assert_same_ctype(self, il_values):
        """Raise ValueError if all IL values do not have the same type."""
        ctype = None
        for il_value in il_values:
            if ctype and ctype != il_value.ctype:
                raise ValueError("different ctypes")


class Add(ILCommand):
    """ADD - adds arg1 and arg2, then saves to output.

    IL values output, arg1, arg2 must all have the same type. No type
    conversion or promotion is done here.

    """

    def __init__(self, output, arg1, arg2): # noqa D102
        self.output = output
        self.arg1 = arg1
        self.arg2 = arg2

        self.assert_same_ctype([output, arg1, arg2])

    def input_values(self): # noqa D102
        return [self.arg1, self.arg2]

    def output_values(self): # noqa D102
        return [self.output]

    def clobber_spots(self): # noqa D102
        # Current implementation lazily clobbers RAX always.
        return [spots.RAX]

    def make_asm(self, spotmap, asm_code): # noqa D102
        ctype = self.arg1.ctype
        arg1_asm = spotmap[self.arg1].asm_str(ctype.size)
        arg2_asm = spotmap[self.arg2].asm_str(ctype.size)
        output_asm = spotmap[self.output].asm_str(ctype.size)
        rax_asm = spots.RAX.asm_str(ctype.size)

        # We can just use "mov" without sign extending because these will be
        # same size.
        asm_code.add_command("mov", rax_asm, arg1_asm)
        asm_code.add_command("add", rax_asm, arg2_asm)
        asm_code.add_command("mov", output_asm, rax_asm)


class Mult(ILCommand):
    """MULT - multiplies arg1 and arg2, then saves to output.

    IL values output, arg1, arg2 must all have the same type. No type
    conversion or promotion is done here.

    """

    def __init__(self, output, arg1, arg2): # noqa D102
        self.output = output
        self.arg1 = arg1
        self.arg2 = arg2

        self.assert_same_ctype([output, arg1, arg2])

    def input_values(self): # noqa D102
        return [self.arg1, self.arg2]

    def output_values(self): # noqa D102
        return [self.output]

    def clobber_spots(self): # noqa D102
        # Current implementation lazily clobbers RAX always.
        return [spots.RAX, spots.RDX, spots.RSI]

    def make_asm(self, spotmap, asm_code): # noqa D102
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


class Div(ILCommand):
    """DIV - divides arg1 and arg2, then saves to output.

    IL values output, arg1, arg2 must all have the same type of size at least
    int. No type conversion or promotion is done here.

    """

    def __init__(self, output, arg1, arg2): # noqa D102
        self.output = output
        self.arg1 = arg1
        self.arg2 = arg2

        self.assert_same_ctype([output, arg1, arg2])

    def input_values(self): # noqa D102
        return [self.arg1, self.arg2]

    def output_values(self): # noqa D102
        return [self.output]

    def clobber_spots(self): # noqa D102
        # RAX/RDX are used by the IDIV command, and RSI is used for moving a
        # literal divisor into a register.
        return [spots.RAX, spots.RDX, spots.RSI]

    def make_asm(self, spotmap, asm_code): # noqa D102
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


class Set(ILCommand):
    """SET - sets output IL value to arg IL value.

    The output IL value and arg IL value need not have the same type. The SET
    command will generate code to convert them as necessary.

    """

    def __init__(self, output, arg): # noqa D102
        self.output = output
        self.arg = arg

    def input_values(self): # noqa D102
        return [self.arg]

    def output_values(self): # noqa D102
        return [self.output]

    def clobber_spots(self): # noqa D102
        # Current implementation lazily clobbers RAX at times.
        return [spots.RAX]

    def make_asm(self, spotmap, asm_code): # noqa D102
        if self.output.ctype == ctypes.bool_t:
            self._set_bool(spotmap, asm_code)
        else:
            arg_spot = spotmap[self.arg]
            output_spot = spotmap[self.output]
            output_asm = output_spot.asm_str(self.output.ctype.size)

            both_stack = (arg_spot.spot_type == Spot.STACK and
                          output_spot.spot_type == Spot.STACK)

            if both_stack:
                temp = spots.RAX.asm_str(self.output.ctype.size)
            else:
                temp = output_asm

            if self.output.ctype.size <= self.arg.ctype.size:
                asm_code.add_command("mov", temp,
                                     arg_spot.asm_str(self.output.ctype.size))
            elif self.output.ctype.size > self.arg.ctype.size:
                if arg_spot.spot_type == Spot.LITERAL:
                    mov = "mov"
                elif self.arg.ctype.signed:
                    mov = "movsx"
                else:
                    mov = "movzx"

                asm_code.add_command(mov, temp,
                                     arg_spot.asm_str(self.arg.ctype.size))

            if both_stack:
                # We can move because rax_asm has same size as output_asm
                asm_code.add_command("mov", output_asm, temp)

    bool_label_num = 0

    def _set_bool(self, spotmap, asm_code):
        """Emit code for SET command if arg is boolean type."""
        # When any scalar value is converted to _Bool, the result is 0 if the
        # value compares equal to 0; otherwise, the result is 1
        arg_asm_old = spotmap[self.arg].asm_str(self.arg.ctype.size)
        if spotmap[self.arg].spot_type == Spot.LITERAL:
            rax_asm = spots.RAX.asm_str(self.arg.ctype.size)
            asm_code.add_command("mov", rax_asm, arg_asm_old)
            arg_asm = rax_asm
        else:
            arg_asm = arg_asm_old

        # TODO: This is kinda hacky
        label = "__shivyc_label_SET_bool" + str(self.bool_label_num)

        output_asm = spotmap[self.output].asm_str(self.output.ctype.size)
        asm_code.add_command("mov", output_asm, "0")
        asm_code.add_command("cmp", arg_asm, "0")
        asm_code.add_command("je", label)
        asm_code.add_command("mov", output_asm, "1")
        asm_code.add_label(label)

        self.bool_label_num += 1


class Return(ILCommand):
    """RETURN - returns the given value from function.

    For now, arg must have type int.

    """

    def __init__(self, arg): # noqa D102
        # arg must already be cast to return type
        self.arg = arg

    def input_values(self): # noqa D102
        return [self.arg]

    def output_values(self): # noqa D102
        return []

    def clobber_spots(self): # noqa D102
        return [spots.RAX]

    def make_asm(self, spotmap, asm_code): # noqa D102
        arg_asm = spotmap[self.arg].asm_str(self.arg.ctype.size)
        rax_asm = spots.RAX.asm_str(self.arg.ctype.size)

        asm_code.add_command("mov", rax_asm, arg_asm)
        asm_code.add_command("mov", "rsp", "rbp")
        asm_code.add_command("pop", "rbp")
        asm_code.add_command("ret")


class Label(ILCommand):
    """Label - Analogous to an ASM label."""

    def __init__(self, label): # noqa D102
        """The label argument is an integer identifier unique to this label."""
        self.label = label

    def input_values(self): # noqa D102
        return []

    def output_values(self): # noqa D102
        return []

    def clobber_spots(self): # noqa D102
        return []

    def make_asm(self, spotmap, asm_code): # noqa D102
        asm_code.add_label(ASMCode.to_label(self.label))


class JumpZero(ILCommand):
    """Jumps to a label if given condition is zero."""

    def __init__(self, cond, label): # noqa D102
        self.cond = cond
        self.label = label

    def input_values(self): # noqa D102
        return [self.cond]

    def output_values(self): # noqa D102
        return []

    def clobber_spots(self): # noqa D102
        return [spots.RAX]

    def make_asm(self, spotmap, asm_code): # noqa D102
        if spotmap[self.cond].spot_type == Spot.LITERAL:
            cond_asm_old = spotmap[self.cond].asm_str(self.cond.ctype.size)
            rax_asm = spots.RAX.asm_str(self.cond.ctype.size)
            asm_code.add_command("mov", rax_asm, cond_asm_old)
            cond_asm = rax_asm
        else:
            cond_asm = spotmap[self.cond].asm_str(self.cond.ctype.size)

        asm_code.add_command("cmp", cond_asm, "0")
        asm_code.add_command("je", ASMCode.to_label(self.label))
