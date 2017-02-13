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
    # A literal value. This is a bit of a hack, since a literal value isn't
    # /really/ a storage spot. The detail attribute is a string representation
    # of the value of this literal.
    LITERAL = 3

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
        # This is hella hacky, but since this function is so well-defined
        # it's OK for now. TODO: When more registers are supported, improve
        # this.
        if self.spot_type == self.REGISTER and size == 4:
            return "e" + self.detail[1] + self.detail[2]
        elif self.spot_type == self.REGISTER and size == 1:
            return self.detail[1] + "l"
        elif self.spot_type == self.STACK and size == 1:
            return "BYTE [rbp-{}]".format(str(abs(self.detail)))
        elif self.spot_type == self.STACK and size == 4:
            return "DWORD [rbp-{}]".format(str(abs(self.detail)))
        elif self.spot_type == self.LITERAL:
            return self.detail
        else:
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
