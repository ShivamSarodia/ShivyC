"""Classes representing IL commands, including procedures to generate asm code
from a given IL command.

"""

import spots

class ILCommand:
    """Base interface for all IL commands"""
    def __init__(self):
        raise NotImplementedError

    def input_values(self):
        """Return set of values read by this command."""
        raise NotImplementedError

    def output_values(self):
        """Return set of values modified by this command."""
        raise NotImplementedError

    def clobber_spots(self):
        """Return set of spots that are clobbered by this command."""
        raise NotImplementedError

    def make_asm(self, spotmap, asm_code):
        """Generate assembly code for this command. Generated assembly can read
        any of the values returned from input_values, may overwrite any values
        returned from output_values, and may change the value of any spots
        returned from clobber_spots without worry.

        asm_code (ASMCode) - Object to which to save generated code.
        spotmap - Dictionary mapping each input/output value to a spot.

        """
        raise NotImplementedError

class AddCommand:
    """ADD - adds arg1 and arg2, then saves to output"""
    def __init__(self, output, arg1, arg2):
        self.output = output
        self.arg1 = arg1
        self.arg2 = arg2

    def input_values(self):
        return {self.arg1, self.arg2}

    def output_values(self):
        return {self.output}

    def clobber_spots(self):
        # Current implementation lazily clobbers RAX always.
        return set(spots.RAX)

    def make_asm(self, spotmap, asm_code):
        arg1_asm = spotmap[self.arg1].asm_str(self.arg1.ctype.size)
        arg2_asm = spotmap[self.arg2].asm_str(self.arg2.ctype.size)
        output_asm = spotmap[self.output].asm_str(self.output.ctype.size)
        rax_asm = spots.RAX.asm_str(self.arg1.ctype.size)

        asm_code.add_command("mov", rax_asm, arg1_asm)
        asm_code.add_command("add", rax_asm, arg2_asm)
        asm_code.add_command("mov", output_asm, rax_asm)
