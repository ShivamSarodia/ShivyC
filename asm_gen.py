"""Objects for the IL->ASM stage of the compiler."""

from collections import namedtuple

import ctypes
import spots
from il_gen import ILCommand
from il_gen import ILValue
from spots import Spot
from spots import SpotSet


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

    value_to_spots (Dict(ILValue -> SpotSet)) - Map from a IL value to a
    set of spots that IL value is stored at.
    spot_to_values (Dict(Spot -> Set(ILValue))) - Map from a spot to a set
    of IL values that are stored at that spot.

    """

    # List of all registers recognized.
    REGISTERS = [spots.RAX, spots.RSI, spots.RDX]

    def __init__(self):
        """Initialize value map."""
        self.value_to_spots = dict()
        self.spot_to_values = dict()

    def spots(self, il_value):
        """Return all spots from which we can currently get this IL value."""
        if il_value not in self.value_to_spots:
            if il_value.value_type == ILValue.TEMP:
                return SpotSet()
            elif il_value.value_type == ILValue.VARIABLE:
                spot = Spot(Spot.STACK, -il_value.offset)
                self._add_value_spot_pair(il_value, spot)
            elif il_value.value_type == ILValue.LITERAL:
                spot = Spot(Spot.LITERAL, il_value.value)
                self._add_value_spot_pair(il_value, spot)

        return self.value_to_spots[il_value]

    def values(self, spot):
        """Return all IL values which are currently stored at this spot."""
        if spot not in self.spot_to_values:
            return set()
        else:
            return self.spot_to_values[spot]

    def set_spots(self, il_value, new_spots):
        """Update the IL value to be stored in the given spots.

        That is, we remove IL value from all spots it was previously stored in,
        and add it to all of the spots provided in the new_spots iterable.

        """
        old_spots = SpotSet(self.spots(il_value))
        new_spots = SpotSet(new_spots)
        for spot in old_spots:
            self._remove_value_spot_pair(il_value, spot)
        for spot in new_spots:
            self._add_value_spot_pair(il_value, spot)

    def forget(self, il_value):
        """Remove all traces of the IL value from the value map.

        Should be called after the last use of an IL value to free up any
        regsters it may have been holding.

        """
        self.set_spots(il_value, SpotSet())

    def get_free_register(self):
        """Return a free register, or None if all registers are occupied."""
        for reg in self.REGISTERS:
            if not self.values(reg):
                return reg

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
            self.value_to_spots[il_value] = SpotSet()

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

    Note: Because this class only has one real public method, we use
    underscore prefix on a method name to indicate that method is meant mostly
    for one-time use in a single function. This class will be refactored once
    it starts to get unwieldy, but right now it's fine as a single class.

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

        self.value_refs = self._value_references()

    def _value_references(self):
        """Get IL value references by line number.

        This functon returns a dictionary mapping every IL value present in the
        provided IL code to an increasing list of line numbers (relative to the
        IL code) where that IL value is referenced. That is, if:

        n in self._value_references(self)[il_value]

        then at least one of self.il_code[n].args[1], self.il_code[n].args[2], or
        self.il_code[n].args[0] is il_value.

        """
        refs = dict()

        def add_to_refs(il_value, line_num):
            if il_value not in refs:
                refs[il_value] = [line_num]
            else:
                refs[il_value].append(line_num)

        for line_num, line in enumerate(self.il_code):
            add_to_refs(line.args[0], line_num)
            add_to_refs(line.args[1], line_num)
            add_to_refs(line.args[2], line_num)

        return refs

    def is_unused_after(self, il_value, line_num):
        """Check if il_value is used after line_num.

        When we support multiple blocks, this function will become more
        complex.

        """
        return max(self.value_refs[il_value]) <= line_num

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

        from_spot = from_spots.best_spot()

        self.asm_code.add_command("mov", to_spot.asm_str(size),
                                  from_spot.asm_str(size))

    def make_asm(self):
        """Generate ASM code.

        Uses the ASMCode and ILCode objects passed to the constructor.

        """
        for line_num, line in enumerate(self.il_code):
            # If we're producing a temporary output and this is would be the
            # only use, then skip this line. TODO: Once we have pointer
            # liveliness anaysis, we can also forget variables if we're sure
            # their values will not be used.
            if (line.args[0] and line.args[0].value_type == ILValue.TEMP and
                    self.is_unused_after(line.args[0], line_num)):
                continue

            arg_spots = self._get_arg_spots(line.args[1], line.args[2])
            self._forget_if_unused(line.args[1], line_num)
            self._forget_if_unused(line.args[2], line_num)

            if line.op == ILCommand.SET:
                self.value_map.set_spots(line.args[0], arg_spots.arg1)
            elif line.op == ILCommand.RETURN:
                self.move_to_spot(arg_spots.arg1, spots.RAX,
                                  line.args[1].ctype.size)
                self.asm_code.add_command("ret")

            # Add literal ints at compile time
            elif (line.op == ILCommand.ADD and
                  line.args[1].ctype == ctypes.integer and
                  line.args[2].ctype == ctypes.integer and
                  arg_spots.arg1.literal_spot() and
                  arg_spots.arg2.literal_spot()):
                arg1_literal = arg_spots.arg1.literal_spot()
                arg2_literal = arg_spots.arg2.literal_spot()
                result_detail = str(
                    int(arg1_literal.detail) + int(arg2_literal.detail))
                self.value_map.set_spots(line.args[0],
                                         {Spot(Spot.LITERAL, result_detail)})

            # One operand is already in a free register
            elif (line.op == ILCommand.ADD and
                  (arg_spots.arg1.free_register_spot(self.value_map) or
                   arg_spots.arg2.free_register_spot(self.value_map))):

                if arg_spots.arg1.free_register_spot(self.value_map):
                    reg_arg, reg_spots = line.args[1], arg_spots.arg1
                    other_arg, other_spots = line.args[2], arg_spots.arg2
                else:
                    reg_arg, reg_spots = line.args[2], arg_spots.arg2
                    other_arg, other_spots = line.args[1], arg_spots.arg1

                reg = reg_spots.free_register_spot(self.value_map)
                self.asm_code.add_command(
                    "add", reg.asm_str(reg_arg.ctype.size),
                    other_spots.best_spot().asm_str(other_arg.ctype.size))
                self.value_map.set_spots(line.args[0], {reg})

            # Grab a free register for the addition
            elif (line.op == ILCommand.ADD and
                  self.value_map.get_free_register()):
                # TODO: Be intelligent on how we pick the free
                # register here. For example, if this value is later
                # the operand of a 'return' statement, then we want to
                # pick RAX. If it's the first argument to a function,
                # we want to pick RSI.
                reg = self.value_map.get_free_register()
                arg1_best = arg_spots.arg1.best_spot()
                arg2_best = arg_spots.arg2.best_spot()
                self.asm_code.add_command(
                    "mov", reg.asm_str(line.args[1].ctype.size),
                    arg1_best.asm_str(line.args[1].ctype.size))
                self.asm_code.add_command(
                    "add", reg.asm_str(line.args[1].ctype.size),
                    arg2_best.asm_str(line.args[1].ctype.size))
                self.value_map.set_spots(line.args[0], {reg})

            # No free registers. We need to spill a value.
            elif line.op == ILCommand.ADD:
                raise NotImplementedError("No free registers")
            elif line.op == ILCommand.MULT:
                raise NotImplementedError
            else:
                raise NotImplementedError

    def _get_arg_spots(self, arg1, arg2):
        """Get information on which spots store the arguments.

        The object returned has an arg1 attribute and an arg2 attribute; each
        is either None if the argument was originally None or a set of
        spots. The sets are copies, so the value map can be modified without
        changing the values of the returned sets.

        """
        ArgSpots = namedtuple("ArgSpots", ["arg1", "arg2"])
        return ArgSpots(
            SpotSet(self.value_map.spots(arg1) if arg1 else None),
            SpotSet(self.value_map.spots(arg2) if arg2 else None))

    def _forget_if_unused(self, arg, line_num):
        """Forget the given argument if it is unused after line_num."""
        if arg and self.is_unused_after(arg, line_num):
            self.value_map.forget(arg)
