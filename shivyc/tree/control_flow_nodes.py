"""Control flow statement nodes in the AST."""

import shivyc.il_cmds.control as control_cmds
from shivyc.errors import CompilerError
from shivyc.tree.base_nodes import Node
from shivyc.tree.utils import report_err, set_type, check_cast


class Return(Node):
    """Node for a return statement."""

    def __init__(self, return_value):
        """Initialize node."""
        super().__init__()
        self.return_value = return_value

    def make_il(self, il_code, symbol_table, c):
        """Make IL code for returning this value."""

        if self.return_value and not c.return_type.is_void():
            il_value = self.return_value.make_il(il_code, symbol_table, c)
            check_cast(il_value, c.return_type, self.return_value.r)
            ret = set_type(il_value, c.return_type, il_code)
            il_code.add(control_cmds.Return(ret))
        elif self.return_value and c.return_type.is_void():
            err = "function with void return type cannot return value"
            raise CompilerError(err, self.r)
        elif not self.return_value and not c.return_type.is_void():
            err = "function with non-void return type must return value"
            raise CompilerError(err, self.r)
        else:
            il_code.add(control_cmds.Return())


class _BreakContinue(Node):
    """Node for a break or continue statement."""

    # Function which accepts a dummy variable and Context and returns the label
    # to which to jump when this statement is encountered.
    get_label = lambda _, c: None
    # "break" if this is a break statement, or "continue" if this is a continue
    # statement
    descrip = None

    def __init__(self):
        """Initialize node."""
        super().__init__()

    def make_il(self, il_code, symbol_table, c):
        """Make IL code for returning this value."""
        label = self.get_label(c)
        if label:
            il_code.add(control_cmds.Jump(label))
        else:
            with report_err():
                err = f"{self.descrip} statement not in loop"
                raise CompilerError(err, self.r)


class Break(_BreakContinue):
    """Node for a break statement."""

    get_label = lambda _, c: c.break_label
    descrip = "break"


class Continue(_BreakContinue):
    """Node for a continue statement."""

    get_label = lambda _, c: c.continue_label
    descrip = "continue"


class IfStatement(Node):
    """Node for an if-statement.

    cond - Conditional expression of the if-statement.
    stat - Body of the if-statement.
    else_statement - Body of the else-statement, or None.

    """

    def __init__(self, cond, stat, else_stat):
        """Initialize node."""
        super().__init__()

        self.cond = cond
        self.stat = stat
        self.else_stat = else_stat

    def make_il(self, il_code, symbol_table, c):
        """Make code for this if statement."""

        endif_label = il_code.get_label()
        with report_err():
            cond = self.cond.make_il(il_code, symbol_table, c)
            il_code.add(control_cmds.JumpZero(cond, endif_label))

        with report_err():
            self.stat.make_il(il_code, symbol_table, c)

        if self.else_stat:
            end_label = il_code.get_label()
            il_code.add(control_cmds.Jump(end_label))
            il_code.add(control_cmds.Label(endif_label))
            with report_err():
                self.else_stat.make_il(il_code, symbol_table, c)
            il_code.add(control_cmds.Label(end_label))
        else:
            il_code.add(control_cmds.Label(endif_label))


class WhileStatement(Node):
    """Node for a while statement.

    cond - Conditional expression of the while-statement.
    stat - Body of the while-statement.

    """

    def __init__(self, cond, stat):
        """Initialize node."""
        super().__init__()
        self.cond = cond
        self.stat = stat

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""
        start = il_code.get_label()
        end = il_code.get_label()

        il_code.add(control_cmds.Label(start))
        c = c.set_continue(start).set_break(end)

        with report_err():
            cond = self.cond.make_il(il_code, symbol_table, c)
            il_code.add(control_cmds.JumpZero(cond, end))

        with report_err():
            self.stat.make_il(il_code, symbol_table, c)

        il_code.add(control_cmds.Jump(start))
        il_code.add(control_cmds.Label(end))


class ForStatement(Node):
    """Node for a for statement.

    first - First clause of the for-statement, or None if not provided.
    second - Second clause of the for-statement, or None if not provided.
    third - Third clause of the for-statement, or None if not provided.
    stat - Body of the for-statement
    """

    def __init__(self, first, second, third, stat):
        """Initialize node."""
        super().__init__()
        self.first = first
        self.second = second
        self.third = third
        self.stat = stat

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""
        symbol_table.new_scope()
        if self.first:
            self.first.make_il(il_code, symbol_table, c)

        start = il_code.get_label()
        cont = il_code.get_label()
        end = il_code.get_label()
        c = c.set_continue(cont).set_break(end)

        il_code.add(control_cmds.Label(start))
        with report_err():
            if self.second:
                cond = self.second.make_il(il_code, symbol_table, c)
                il_code.add(control_cmds.JumpZero(cond, end))

        with report_err():
            self.stat.make_il(il_code, symbol_table, c)

        il_code.add(control_cmds.Label(cont))

        with report_err():
            if self.third:
                self.third.make_il(il_code, symbol_table, c)

        il_code.add(control_cmds.Jump(start))
        il_code.add(control_cmds.Label(end))

        symbol_table.end_scope()
