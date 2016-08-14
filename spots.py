"""The Spot object definition and and some predefined spots, like registers."""

from collections.abc import MutableSet


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
        # This is kinda hacky, but since this function is so well-defined
        # it's OK for now. TODO: When more registers are supported, improve
        # this.
        if self.spot_type == self.REGISTER and size == 4:
            return "e" + self.detail[1] + self.detail[2]
        elif self.spot_type == self.STACK and size == 4:
            if self.detail > 0:
                return "DWORD [rbp+{}]".format(str(abs(self.detail)))
            elif self.detail == 0:
                return "DWORD [rbp]"
            else:
                return "DWORD [rbp-{}]".format(str(abs(self.detail)))
        elif self.spot_type == self.LITERAL:
            return self.detail
        else:
            raise NotImplementedError("Unsupported spot_type/size combo")

    @staticmethod
    def better(spot1, spot2):
        """Check if self is preferred over the other spot.

        Specifically, we prefer a register spot over a literal spot over a
        stack spot.

        """
        if not spot2:
            return spot1
        if not spot1:
            return spot2
        elif spot1.spot_type == Spot.REGISTER:
            return spot1
        elif spot2.spot_type == Spot.REGISTER:
            return spot2
        elif spot1.spot_type == Spot.LITERAL:
            return spot1
        elif spot2.spot_type == Spot.LITERAL:
            return spot2
        else:  # both are stack
            return spot1

    # It's very important spots to compare equal iff they have the same type
    # and detail, so the ASM generation step can keep track of their values as
    # one unit.
    def __eq__(self, other):
        """Test equality by comparing type and detail."""
        return (self.spot_type, self.detail) == (other.spot_type, other.detail)

    def __hash__(self):
        """Hash based on type and detail."""
        return hash((self.spot_type, self.detail))


class SpotSet(MutableSet):
    """Unordered collection of Spot objects."""

    def __init__(self, spots=None):
        """Initialize SpotSet."""
        if spots:
            # Copy the provided set
            self.spots = set(spots)
        else:
            self.spots = set()

    def literal_spot(self):
        """Return a literal spot in this spot set, if possible."""
        for spot in self.spots:
            if spot.spot_type == Spot.LITERAL:
                return spot

    def free_register_spot(self, value_map):
        """Return a free register spot in this spot set, if possible."""
        for spot in self.spots:
            if spot.spot_type == Spot.REGISTER and not value_map.values(spot):
                return spot

    def best_spot(self):
        """Pick the best spot in this spot set.

        If this set contains a register spot, pick that one. Next best is a
        literal spot, and worst-case is a stack spot. Returns the best spot it
        finds, or None if the spot set is empty.

        """
        best_spot = None
        for spot in self.spots:
            best_spot = Spot.better(best_spot, spot)
        return best_spot

    # Implement the Set abstact methods
    def __contains__(self, spot):  # noqa: D102, D105
        return spot in self.spots

    def __iter__(self):  # noqa: D102, D105
        return iter(self.spots)

    def __len__(self):  # noqa: D102, D105
        return len(self.spots)

    def add(self, spot):  # noqa: D102, D105
        self.spots.add(spot)

    def discard(self, spot):  # noqa: D102, D105
        self.spots.discard(spot)


RAX = Spot(Spot.REGISTER, "rax")
RSI = Spot(Spot.REGISTER, "rsi")
RDX = Spot(Spot.REGISTER, "rdx")
