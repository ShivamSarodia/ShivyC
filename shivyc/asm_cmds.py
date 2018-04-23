"""This module defines and implements classes representing assembly commands.

The _ASMCommand object is the base class for most ASM commands. Some commands
inherit from _ASMCommandMultiSize or _JumpCommand instead.

"""


class _ASMCommand:
    """Base class for a standard ASMCommand, like `add` or `imul`.

    This class is used for ASM commands which take arguments of the same
    size.
    """

    name = None

    def __init__(self, dest=None, source=None, size=None):
        self.dest = dest.asm_str(size) if dest else None
        self.source = source.asm_str(size) if source else None
        self.size = size

    def __str__(self):
        s = "\t" + self.name
        if self.dest:
            s += " " + self.dest
        if self.source:
            s += ", " + self.source
        return s


class _ASMCommandMultiSize:
    """Base class for an ASMCommand which takes arguments of different sizes.

    For example, `movsx` and `movzx`.
    """

    name = None

    def __init__(self, dest, source, source_size, dest_size):
        self.dest = dest.asm_str(source_size)
        self.source = source.asm_str(dest_size)
        self.source_size = source_size
        self.dest_size = dest_size

    def __str__(self):
        s = "\t" + self.name
        if self.dest:
            s += " " + self.dest
        if self.source:
            s += ", " + self.source
        return s


class _JumpCommand:
    """Base class for jump commands."""

    name = None

    def __init__(self, target):
        self.target = target

    def __str__(self):
        s = "\t" + self.name + " " + self.target
        return s


class Comment:
    """Class for comments."""

    def __init__(self, msg):  # noqa: D102
        self.msg = msg

    def __str__(self):  # noqa: D102
        return "\t// " + self.msg


class Label:
    """Class for label."""

    def __init__(self, label):  # noqa: D102
        self.label = label

    def __str__(self):  # noqa: D102
        return self.label + ":"


class Lea:
    """Class for lea command."""

    name = "lea"

    def __init__(self, dest, source):  # noqa: D102
        self.dest = dest
        self.source = source

    def __str__(self):  # noqa: D102
        return ("\t" + self.name + " " + self.dest.asm_str(8) + ", "
                "" + self.source.asm_str(0))


class Je(_JumpCommand): name = "je"  # noqa: D101


class Jne(_JumpCommand): name = "jne"  # noqa: D101


class Jg(_JumpCommand): name = "jg"  # noqa: D101


class Jge(_JumpCommand): name = "jge"  # noqa: D101


class Jl(_JumpCommand): name = "jl"  # noqa: D101


class Jle(_JumpCommand): name = "jle"  # noqa: D101


class Ja(_JumpCommand): name = "ja"  # noqa: D101


class Jae(_JumpCommand): name = "jae"  # noqa: D101


class Jb(_JumpCommand): name = "jb"  # noqa: D101


class Jbe(_JumpCommand): name = "jbe"  # noqa: D101


class Jmp(_JumpCommand): name = "jmp"  # noqa: D101


class Movsx(_ASMCommandMultiSize): name = "movsx"  # noqa: D101


class Movzx(_ASMCommandMultiSize): name = "movzx"  # noqa: D101


class Mov(_ASMCommand): name = "mov"  # noqa: D101


class Add(_ASMCommand): name = "add"  # noqa: D101


class Sub(_ASMCommand): name = "sub"  # noqa: D101


class Neg(_ASMCommand): name = "neg"  # noqa: D101


class Not(_ASMCommand): name = "not"  # noqa: D101


class Div(_ASMCommand): name = "div"  # noqa: D101


class Imul(_ASMCommand): name = "imul"  # noqa: D101


class Idiv(_ASMCommand): name = "idiv"  # noqa: D101


class Cdq(_ASMCommand): name = "cdq"  # noqa: D101


class Cqo(_ASMCommand): name = "cqo"  # noqa: D101


class Xor(_ASMCommand): name = "xor"  # noqa: D101


class Cmp(_ASMCommand): name = "cmp"  # noqa: D101


class Pop(_ASMCommand): name = "pop"  # noqa: D101


class Push(_ASMCommand): name = "push"  # noqa: D101


class Call(_ASMCommand): name = "call"  # noqa: D101


class Ret(_ASMCommand): name = "ret"  # noqa: D101


class Sar(_ASMCommandMultiSize): name = "sar"  # noqa: D101


class Sal(_ASMCommandMultiSize): name = "sal"  # noqa: D101
