"""Base ILCommand interface definition."""

import shivyc.ctypes as ctypes
from shivyc.spots import LiteralSpot


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

        In addition, the PRL may have a None key. The value of this key is a
        list of ILValue which are being internally referenced, but no
        pointers to them are being externally returned.
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

    def _is_imm(self, spot):
        """Return True iff given spot is an immediate operand."""
        return isinstance(spot, LiteralSpot)

    def _is_imm8(self, spot):
        """Return True if given spot is a 8-bit immediate operand."""
        return self._is_imm(spot) and int(spot.detail) < ctypes.unsig_char_max

    def _is_imm64(self, spot):
        """Return True if given spot is a 64-bit immediate operand."""
        return (isinstance(spot, LiteralSpot) and
                (int(spot.detail) > ctypes.int_max or
                 int(spot.detail) < ctypes.int_min))
