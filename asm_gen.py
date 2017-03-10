"""Objects for the IL->ASM stage of the compiler."""

import spots
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
        self.externs = []

    def add_command(self, command, arg1=None, arg2=None):
        """Add a command to the code.

        command (str) - Name of the command to add.
        arg1 (str) - First argument of the command.
        arg2 (str) - Second argument of the command.

        """
        self.lines.append((command, arg1, arg2))

    label_num = 0

    @staticmethod
    def get_label():
        """Return a unique label string."""
        ASMCode.label_num += 1
        return "__shivyc_label" + str(ASMCode.label_num)

    def add_label(self, label):
        """Add a label to the code.

        label (str) - The label string to add.

        """
        self.lines.append(label)

    def add_extern(self, name):
        """Add an external name to the code.

        name (str) - The name to add.

        """
        self.externs.append("extern " + name)

    def add_comment(self, comment):
        """Add a comment in the ASM code."""
        self.lines.append(";; " + comment)

    def full_code(self):  # noqa: D202
        """Produce the full assembly code.

        return (str) - The assembly code, ready for saving to disk and
        assembling.

        """

        def to_string(line):
            """Convert the provided tuple/string into a string of asm code.

            Does not terminate with a newline.

            """
            if isinstance(line, str):
                if line[:2] == ";;":  # this is a comment
                    return "     " + line
                else:  # this is a label
                    return line + ":"
            else:
                line_str = "     " + line[0]
                if line[1]:
                    line_str += " " + line[1]
                if line[2]:
                    line_str += ", " + line[2]
                return line_str

        # This code starts every asm program so far, so we put it here.
        header = self.externs + ["global main", "", "main:"]

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
            if value in self.il_code.literals:
                spotmap[value] = Spot(Spot.LITERAL,
                                      self.il_code.literals[value])
            elif self.il_code.variables.get(value, None):
                # If there is a preassigned spot, continue
                spotmap[value] = Spot(Spot.MEM, self.il_code.variables[value])
            else:
                # Allocate stack spots for all temps and variables
                offset += value.ctype.size
                spotmap[value] = Spot(Spot.MEM, ("rbp", -offset))

        for extern in self.il_code.externs:
            self.asm_code.add_extern(extern)

        # Back up rbp and move rsp
        self.asm_code.add_command("push", "rbp")
        self.asm_code.add_command("mov", "rbp", "rsp")
        self.asm_code.add_command("sub", "rsp", str(offset))

        # Generate all asm code
        for command in self.il_code:
            self.asm_code.add_comment(type(command).__name__.upper())

            def get_reg(x=[], y=[]):
                return spots.RAX
            command.make_asm(spotmap, spotmap, get_reg, self.asm_code)

    def _all_il_values(self):
        """Return a list of all IL values that appear in the IL code."""
        all_values = []
        for command in self.il_code:
            for value in command.inputs() + command.outputs():
                if value not in all_values:
                    all_values.append(value)

        return all_values
