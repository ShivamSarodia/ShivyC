"""The Spot object definition and and some predefined spots, like registers."""


class Spot:
    """Spot in the machine where an IL value can be.

    spot_type (enum) - One of the values below describing the general type of
    spot this is.
    detail - Additional information about this spot. The this attribute's type
    and meaning depend on the spot_type; see below for more.

    """

    # Options for spot_type:
    # Register spot. The `detail` attribute is the full 64-bit register name
    # (rax, rdi, etc.) as a string.
    REGISTER = 1
    # Stack spot. The `detail` attribute is an integer representing the offset
    # from rbp, usually negative.
    STACK = 2
    # Data spot. The `detail` attribute is the name of the value in data, like
    # function name or static variable name.
    DATA = 3
    # A literal value. This is a bit of a hack, since a literal value isn't
    # /really/ a storage spot. The detail attribute is a string representation
    # of the value of this literal.
    LITERAL = 4

    def __init__(self, spot_type, detail):
        """Initialize a spot."""
        self.spot_type = spot_type
        self.detail = detail

    def asm_str(self, size):
        """Make the ASM form of this spot, for the given size in bytes.

        This function raises NotImplementedError for unsupported sizes.

        Examples:
            spots.RAX.asm_str(4) -> "eax"
            spots.RAX.asm_str(8) -> "rax"
            spot(STACK, -16).asm_str(4) -> "DWORD [rbp-16]"
            spot(LITERAL, 14).asm_str(4) -> "14"

        size (int) - Size in bytes of the data stored at this spot.
        return (str) - ASM form of this spot.

        """
        # TODO: Do I need rex prefix on any of the 8-bit?
        spot_map = {"rax": ["rax", "eax", "ax", "al"],
                    "rsi": ["rsi", "esi", "si", "sil"],
                    "rdx": ["rdx", "edx", "dx", "dl"],
                    "rdi": ["rdi", "edi", "di", "dil"]}

        if self.spot_type == self.REGISTER:
            if size == 1: return spot_map[self.detail][3]
            elif size == 2: return spot_map[self.detail][2]
            elif size == 4: return spot_map[self.detail][1]
            elif size == 8: return spot_map[self.detail][0]
        elif self.spot_type == self.STACK or self.spot_type == self.DATA:
            if size == 1: size_desc = "BYTE"
            elif size == 2: size_desc = "WORD"
            elif size == 4: size_desc = "DWORD"
            elif size == 8: size_desc = "QWORD"

            if self.spot_type == self.STACK:
                addr = "rbp-" + str(abs(self.detail))
            else:  # self.DATA
                addr = self.detail

            return size_desc + " [{}]".format(addr)

        elif self.spot_type == self.LITERAL:
            return self.detail

        raise NotImplementedError("Unsupported spot_type/size combo")

    def __eq__(self, other):
        """Test equality by comparing type and detail."""
        return (self.spot_type, self.detail) == (other.spot_type, other.detail)

    def __hash__(self):
        """Hash based on type and detail."""
        return hash((self.spot_type, self.detail))

RAX = Spot(Spot.REGISTER, "rax")
RSI = Spot(Spot.REGISTER, "rsi")
RDX = Spot(Spot.REGISTER, "rdx")
RDI = Spot(Spot.REGISTER, "rdi")
