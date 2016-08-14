"""Objects for the IL->ASM stage of the compiler."""

import ctypes
import spots
from il_gen import ILCode
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


class ValueMap:
    """Tracks the correspondence between IL values and machine storage.

    value_to_spots (Dict(ILValue -> Set(Spot))) - Map from a IL value to a list
    of spots that IL value is stored at.
    spot_to_values (Dict(Spot -> Set(ILValue))) - Map from a spot to a list of
    IL values that are stored at that spot.

    """

    def __init__(self):
        """Initialize value map."""
        self.value_to_spots = dict()
        self.spot_to_values = dict()

    def spots(self, il_value):
        """Return all spots from which we can currently get this IL value."""
        if il_value not in self.value_to_spots:
            if il_value.value_type == ILValue.TEMP:
                # Direct access here is OK because we aren't associating with
                # any spot.
                self.value_to_spots[il_value] = set()
            elif il_value.value_type == ILValue.VARIABLE:
                spot = Spot(Spot.STACK, -il_value.offset)
                self._add_value_spot_pair(il_value, spot)
            elif il_value.value_type == ILValue.LITERAL:
                spot = Spot(Spot.LITERAL, il_value.value)
                self._add_value_spot_pair(il_value, spot)

        return self.value_to_spots[il_value]

    def set_spots(self, il_value, new_spots):
        """Update the IL value to be stored in the given spots.

        That is, we remove IL value from all spots it was previously stored in,
        and add it to all of the spots provided.

        """
        old_spots = set(self.spots(il_value))
        new_spots = set(new_spots)
        for spot in old_spots:
            self._remove_value_spot_pair(il_value, spot)
        for spot in new_spots:
            self._add_value_spot_pair(il_value, spot)

    def forget(self, il_value):
        """Remove all traces of the IL value from the value map.

        Should be called after the last use of an IL value to free up any
        regsters it may have been holding.

        """
        self.set_spots(il_value, set())

    def _add_value_spot_pair(self, il_value, spot):
        """Add a value-spot pair without considering value/spot types.

        Even internally, use this and the _remove_spot... function instead of
        directly accessing the value_to_spots and spot_to_values dictionaries,
        because these functions make sure the two dictionaries are kept in
        sync.

        """
        if spot not in self.spot_to_values:
            self.spot_to_values[spot] = set()
        if il_value not in self.value_to_spots:
            self.value_to_spots[il_value] = set()

        self.value_to_spots[il_value].add(spot)
        self.spot_to_values[spot].add(il_value)

    def _remove_value_spot_pair(self, il_value, spot):
        """Remove a value-spot pair without considering value/spot types.

        This function raises an exception if the pair is not found.

        Even internally, use this and the _add_spot... function instead of
        directly accessing the value_to_spots and spot_to_values dictionaries,
        because these functions make sure the two dictionaries are kept in
        sync.

        """
        self.value_to_spots[il_value].remove(spot)
        self.spot_to_values[spot].remove(il_value)

        if not self.value_to_spots[il_value]:
            del self.value_to_spots[il_value]
        if not self.spot_to_values[spot]:
            del self.spot_to_values[spot]


class ASMGen:
    """Contains the main logic for generation of the ASM from the IL.

    Note: This class will be refactored once it starts to get unweildy, but
    right now it's fine as a single class.

    il_code (ILCode) - IL code to convert to ASM.
    asm_code (ASMCode) - ASMCode object to populate with ASM.

    value_map (ValueMap) - Internal object storing the current value map.
    value_refs (dict(ILValue->List(int))) - Internal object storing the
    references by line number of each IL value.

    """

    def __init__(self, il_code, asm_code):
        """Initialize ASMGen."""
        self.il_code = il_code
        self.asm_code = asm_code
        self.value_map = ValueMap()

        self.value_refs = self.value_references()

    def value_references(self):
        """Get IL value references by line number.

        This functon returns a dictionary mapping every IL value present in the
        provided IL code to an increasing list of line numbers (relative to the
        IL code) where that IL value is referenced. That is, if:

        n in self.value_references(self)[il_value]

        then at least one of self.il_code[n].arg1, self.il_code[n].arg2, or
        self.il_code[n].output is il_value.

        """
        refs = dict()

        def add_to_refs(il_value, line_num):
            if il_value not in refs:
                refs[il_value] = [line_num]
            else:
                refs[il_value].append(line_num)

        for line_num, line in enumerate(self.il_code):
            add_to_refs(line.output, line_num)
            add_to_refs(line.arg1, line_num)
            add_to_refs(line.arg2, line_num)

        return refs

    def is_forgettable(self, il_value, line_num):
        """Check if il_value is used after line_num.

        When we support multiple blocks, this function will become more
        complex.

        """
        return max(self.value_refs[il_value]) <= line_num

    def make_asm(self):
        """Generate ASM code.

        Uses the ASMCode and ILCode objects passed to the constructor.

        """
        for line_num, line in enumerate(self.il_code):
            # If we're producing a temporary output and this is would be the
            # only use, then skip this line.
            if (line.output and line.output.value_type == ILValue.TEMP and
                    self.is_forgettable(line.output, line_num)):
                continue

            if line.command == ILCode.SET:
                arg_spots = self.value_map.spots(line.arg1)
                self.value_map.set_spots(line.output, arg_spots)

                if self.is_forgettable(line.arg1, line_num):
                    self.value_map.forget(line.arg1)
            elif line.command == ILCode.RETURN:
                self.move_to_spot(
                    self.value_map.spots(line.arg1), spots.RAX,
                    line.arg1.ctype.size)
                self.asm_code.add_command("ret")
            elif line.command == ILCode.ADD:
                arg1_spots = set(self.value_map.spots(line.arg1))
                arg2_spots = set(self.value_map.spots(line.arg2))

                # Forget the arguments if possible, so we can reuse those
                # registers.
                if self.is_forgettable(line.arg1, line_num):
                    self.value_map.forget(line.arg1)
                if self.is_forgettable(line.arg2, line_num):
                    self.value_map.forget(line.arg2)

                # If they're both literal ints, add them at compile time.
                if (line.arg1.ctype == ctypes.integer and
                        line.arg2.ctype == ctypes.integer and
                        self.get_literal_spot(arg1_spots) and
                        self.get_literal_spot(arg2_spots)):
                    arg1_literal = self.get_literal_spot(arg1_spots)
                    arg2_literal = self.get_literal_spot(arg2_spots)
                    result_detail = str(
                        int(arg1_literal.detail) + int(arg2_literal.detail))
                    self.value_map.set_spots(
                        line.output, {Spot(Spot.LITERAL, result_detail)})
                else:
                    raise NotImplementedError
            elif line.command == ILCode.MULT:
                raise NotImplementedError
            else:
                raise NotImplementedError

    def get_literal_spot(self, spots):
        """Find a literal spot from the given spots, if possible.

        If any of spots is a literal spot, return it. If not, return None.

        """
        for spot in spots:
            if spot.spot_type == Spot.LITERAL:
                return spot

    def best_spot(self, spots):
        """Pick the best spot from the given list of spots.

        Best is a register spot, next best is a literal spot, worst-case is a
        stack spot. Returns the best spot it finds, or None if spots is empty.

        """
        best_spot = None
        for spot in spots:
            # TODO: Pick the best register, not just the first one
            # encountered.
            if spot.spot_type == Spot.REGISTER:
                return spot
            elif spot.spot_type == Spot.LITERAL:
                best_spot = spot
            elif spot.spot_type == Spot.STACK and not best_spot:
                best_spot = spot
        return best_spot

    def move_to_spot(self, from_spots, to_spot, size):
        """Make asm code to move the given IL value to the given spot.

        This function is currently very dangerous--it overwrites the value of
        the spot without updating the value map. Hence, it should only be used
        at the very end of a block. This will be fixed as needed. If the
        il_value is already in the given register, may not produce any ASM
        code.

        """
        if to_spot.spot_type != Spot.REGISTER:
            raise NotImplementedError(
                "Only register spots currently supported")

        # Check if the value is already in the desired spot
        if any(spot == to_spot for spot in from_spots):
            return

        from_spot = self.best_spot(from_spots)

        self.asm_code.add_command("mov", to_spot.asm_str(size),
                                  from_spot.asm_str(size))
