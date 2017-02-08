"""Objects for the IL->ASM stage of the compiler."""

from collections import namedtuple

import ctypes
import spots
from il_gen import ILValue
from spots import Spot

class ASMCode:
    """Stores the ASM code generated from the IL code.

    lines (List) - Lines of ASM code recorded. The commands are stored as
    tuples in this list, where the first value is the name of the command and
    the next values are the command arguments.

    """

    def __init__(self):
        """Initialize ASMCode."""
        self.lines = []

    def add_command(self, command, arg1=None, arg2=None):
        """Add a command to the code.

        command (str) - Name of the command to add.
        arg1 (str) - First argument of the command.
        arg2 (str) - Second argument of the command.

        """
        self.lines.append((command, arg1, arg2))

    def full_code(self):  # noqa: D202
        """Produce the full assembly code.

        return (str) - The assembly code, ready for saving to disk and
        assembling.

        """

        def to_string(line):
            """Convert the provided tuple into a string of asm code.

            Does not terminate with a newline.

            """
            line_str = "     " + line[0]
            if line[1]:
                line_str += " " + line[1]
            if line[2]:
                line_str += ", " + line[2]
            return line_str

        # This code starts every asm program so far, so we put it here.
        header = ["global main", "", "main:"]

        return "\n".join(header + [to_string(line) for line in self.lines])

class ASMGen:
    """Contains the main logic for generation of the ASM from the IL.

    il_code (ILCode) - IL code to convert to ASM.
    asm_code (ASMCode) - ASMCode object to populate with ASM.

    """

    def __init__(self, il_code, asm_code):
        """Initialize ASMGen."""
        self.il_code = il_code
        self.asm_code = asm_code

    def make_asm(self):
        """Generate ASM code.

        Uses the ASMCode and ILCode objects passed to the constructor.

        """
        # Generate spotmap where each value is stored somewhere on the stack.
        all_values = self._all_il_values()

        offset = 0
        spotmap = {}
        for value in all_values:
            if value.value_type == ILValue.LITERAL:
                spotmap[value] = Spot(Spot.LITERAL, value.value)
            else:
                offset += value.ctype.size
                spotmap[value] = Spot(Spot.STACK, -offset)

        # Back up rbp and move rsp
        self.asm_code.add_command("push", "rbp")
        self.asm_code.add_command("mov", "rbp", "rsp")

        # Generate all asm code
        for command in self.il_code:
            command.make_asm(spotmap, self.asm_code)

    def _all_il_values(self):
        """Return a list of all IL values that appear in the IL code."""
        all_values = []
        for command in self.il_code:
            for value in command.input_values() + command.output_values():
                if value not in all_values: all_values.append(value)

        return all_values
