"""Classes representing IL commands.

Each IL command is represented by a class that inherits from the ILCommand
interface. The implementation provides code that generates ASM for each IL
command.

"""

import spots
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


class Add(ILCommand):
    """ADD - adds arg1 and arg2, then saves to output."""

    def __init__(self, output, arg1, arg2): # noqa D102
        self.output = output
        self.arg1 = arg1
        self.arg2 = arg2

    def input_values(self): # noqa D102
        return [self.arg1, self.arg2]

    def output_values(self): # noqa D102
        return [self.output]

    def clobber_spots(self): # noqa D102
        # Current implementation lazily clobbers RAX always.
        return [spots.RAX]

    def make_asm(self, spotmap, asm_code): # noqa D102
        arg1_asm = spotmap[self.arg1].asm_str(self.arg1.ctype.size)
        arg2_asm = spotmap[self.arg2].asm_str(self.arg2.ctype.size)
        output_asm = spotmap[self.output].asm_str(self.output.ctype.size)
        rax_asm = spots.RAX.asm_str(self.arg1.ctype.size)

        asm_code.add_command("mov", rax_asm, arg1_asm)
        asm_code.add_command("add", rax_asm, arg2_asm)
        asm_code.add_command("mov", output_asm, rax_asm)


class Mult(ILCommand):
    """MULT - multiplies arg1 and arg2, then saves to output."""

    def __init__(self, output, arg1, arg2): # noqa D102
        self.output = output
        self.arg1 = arg1
        self.arg2 = arg2

    def input_values(self): # noqa D102
        return [self.arg1, self.arg2]

    def output_values(self): # noqa D102
        return [self.output]

    def clobber_spots(self): # noqa D102
        # Current implementation lazily clobbers RAX always.
        return [spots.RAX]

    def make_asm(self, spotmap, asm_code): # noqa D102
        arg1_asm = spotmap[self.arg1].asm_str(self.arg1.ctype.size)
        arg2_asm = spotmap[self.arg2].asm_str(self.arg2.ctype.size)
        output_asm = spotmap[self.output].asm_str(self.output.ctype.size)
        rax_asm = spots.RAX.asm_str(self.arg1.ctype.size)

        asm_code.add_command("mov", rax_asm, arg1_asm)
        asm_code.add_command("imul", rax_asm, arg2_asm)
        asm_code.add_command("mov", output_asm, rax_asm)


class Set(ILCommand):
    """SET - sets output IL value to arg IL value."""

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
        arg_spot = spotmap[self.arg]
        output_spot = spotmap[self.output]

        arg_asm = arg_spot.asm_str(self.arg.ctype.size)
        output_asm = output_spot.asm_str(self.output.ctype.size)
        rax_asm = spots.RAX.asm_str(self.arg.ctype.size)

        # TODO: What to do if output is literal spot? Will this be caught
        # before?

        # Cannot move stack spot directly to another stack spot
        if (arg_spot.spot_type == Spot.STACK and
             output_spot.spot_type == Spot.STACK):
            asm_code.add_command("mov", rax_asm, arg_asm)
            asm_code.add_command("mov", output_asm, rax_asm)
        else:
            asm_code.add_command("mov", output_asm, arg_asm)


class Return(ILCommand):
    """RETURN - returns the given value from function."""

    def __init__(self, arg): # noqa D102
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
