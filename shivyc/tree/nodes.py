"""Nodes in the AST which represent statements or declarations."""

import shivyc.ctypes as ctypes
import shivyc.decl_tree as decl_tree
import shivyc.il_cmds.control as control_cmds
import shivyc.token_kinds as token_kinds

from shivyc.ctypes import PointerCType, ArrayCType, FunctionCType
from shivyc.errors import CompilerError
from shivyc.il_gen import ILValue
from shivyc.tree.utils import LValue, report_err, set_type, check_cast


class Node:
    """Base class for representing a single node in the AST.

    All AST nodes inherit from this class.
    """

    def __init__(self):
        """Initialize node."""

        # Set range to None because it will be set by the parser.
        self.r = None

    def make_il(self, il_code, symbol_table, c):
        """Generate IL code for this node.

        il_code - ILCode object to add generated code to.
        symbol_table - Symbol table for current node.
        c - Context for current node, as above. This function should not
        modify this object.
        """
        raise NotImplementedError


class Root(Node):
    """Root node of the program."""

    def __init__(self, nodes):
        """Initialize node."""
        super().__init__()
        self.nodes = nodes

    def make_il(self, il_code, symbol_table, c):
        """Make code for the root."""
        for node in self.nodes:
            with report_err():
                c = c.set_global(True)
                node.make_il(il_code, symbol_table, c)


class Main(Node):
    """Node for the main function."""

    def __init__(self, body):
        """Initialize node."""
        super().__init__()
        self.body = body

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""

        # This node will have c.is_global set True, so we must change it to
        # for the children context.
        c = c.set_global(False)
        self.body.make_il(il_code, symbol_table, c)

        zero = ILValue(ctypes.integer)
        il_code.register_literal_var(zero, 0)
        il_code.add(control_cmds.Return(zero))


class Compound(Node):
    """Node for a compound statement."""

    def __init__(self, items):
        """Initialize node."""
        super().__init__()
        self.items = items

    def make_il(self, il_code, symbol_table, c):
        """Make IL code for every block item, in order."""
        symbol_table.new_scope()
        c = c.set_global(False)
        for item in self.items:
            with report_err():
                item.make_il(il_code, symbol_table, c)
        symbol_table.end_scope()


class Return(Node):
    """Node for a return statement."""

    def __init__(self, return_value):
        """Initialize node."""
        super().__init__()
        self.return_value = return_value

    def make_il(self, il_code, symbol_table, c):
        """Make IL code for returning this value."""
        il_value = self.return_value.make_il(il_code, symbol_table, c)

        check_cast(il_value, ctypes.integer, self.return_value.r)

        ret = set_type(il_value, ctypes.integer, il_code)
        il_code.add(control_cmds.Return(ret))


class ExprStatement(Node):
    """Node for a statement which contains one expression."""

    def __init__(self, expr):
        """Initialize node."""
        super().__init__()
        self.expr = expr

    def make_il(self, il_code, symbol_table, c):
        """Make code for this expression, and ignore the resulting ILValue."""
        self.expr.make_il(il_code, symbol_table, c)


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
        end = il_code.get_label()

        il_code.add(control_cmds.Label(start))
        with report_err():
            if self.second:
                cond = self.second.make_il(il_code, symbol_table, c)
                il_code.add(control_cmds.JumpZero(cond, end))

        with report_err():
            self.stat.make_il(il_code, symbol_table, c)

        with report_err():
            if self.third:
                self.third.make_il(il_code, symbol_table, c)

        il_code.add(control_cmds.Jump(start))
        il_code.add(control_cmds.Label(end))

        symbol_table.end_scope()


class Declaration(Node):
    """Line of a general variable declaration(s).

    decls (List(decl_tree.Node)) - list of declaration trees
    inits (List(Expression Node)) - list of initializer expressions, or None
    if a variable is not initialized
    """

    def __init__(self, decls, inits):
        """Initialize node."""
        super().__init__()
        self.decls = decls
        self.inits = inits

    # Storage class specifiers for declarations
    AUTO = 0
    STATIC = 1
    EXTERN = 2

    def make_il(self, il_code, symbol_table, c):
        """Make code for this declaration."""
        for decl, init in zip(self.decls, self.inits):
            with report_err():
                self.process(decl, init, il_code, symbol_table, c)

    def process(self, decl, init, il_code, symbol_table, c):
        """Process givn decl/init pair."""
        ctype, identifier, storage = self.make_ctype(decl)
        if not identifier:
            err = "missing identifier name in declaration"
            raise CompilerError(err, decl.r)

        if ctype == ctypes.void:
            err = "variable of void type declared"
            raise CompilerError(err, decl.r)

        var = symbol_table.add(identifier, ctype)

        # Variables declared to be EXTERN
        if storage == self.EXTERN:
            il_code.register_extern_var(var, identifier.content)

            # Extern variable should not have initializer
            if init:
                err = "extern variable has initializer"
                raise CompilerError(err, decl.r)

        # Variables declared to be static
        elif storage == self.STATIC:
            # These should be in .data section, but not global
            raise NotImplementedError("static variables unsupported")

        # Global variables
        elif c.is_global:
            # Global functions are extern by default
            if ctype.is_function():
                il_code.register_extern_var(var, identifier.content)
            else:
                # These should be common if uninitialized, or data if
                # initialized
                raise NotImplementedError(
                    "non-extern global variables unsupported")

        # Local variables
        else:
            il_code.register_local_var(var)

        # Initialize variable if needed
        if init:
            init_val = init.make_il(il_code, symbol_table, c)
            lval = LValue(LValue.DIRECT, var)
            if lval.modable():
                lval.set_to(init_val, il_code, identifier.r)
            else:
                err = "declared variable is not of assignable type"
                raise CompilerError(err, decl.r)

    def make_ctype(self, decl, prev_ctype=None, storage=0):
        """Generate a ctype from the given declaration.

        Return a `ctype, identifier token, storage class` triple.

        decl - Node of decl_tree to parse. See decl_tree.py for explanation
        about decl_trees.
        prev_ctype - The ctype formed from all parts of the tree above the
        current one.
        storage - The storage class of this declaration.
        """
        if isinstance(decl, decl_tree.Root):
            ctype, storage = self.make_specs_ctype(decl.specs)
            return self.make_ctype(decl.child, ctype, storage)
        elif isinstance(decl, decl_tree.Pointer):
            return self.make_ctype(decl.child, PointerCType(prev_ctype),
                                   storage)
        elif isinstance(decl, decl_tree.Array):
            return self.make_ctype(decl.child, ArrayCType(prev_ctype, decl.n),
                                   storage)
        elif isinstance(decl, decl_tree.Function):
            args = [self.make_ctype(decl)[0] for decl in decl.args]
            return self.make_ctype(decl.child,
                                   FunctionCType(args, prev_ctype),
                                   storage)
        elif isinstance(decl, decl_tree.Identifier):
            return prev_ctype, decl.identifier, storage

    def make_specs_ctype(self, specs):
        """Make a ctype out of the provided list of declaration specifiers.

        Return a `ctype, storage class` pair, where storage class is one of
        the above values.
        """
        spec_range = specs[0].r + specs[-1].r

        spec_kinds = [spec.kind for spec in specs]
        base_type_list = list(set(ctypes.simple_types.keys()) &
                              set(spec_kinds))
        if len(base_type_list) == 0:
            base_type = ctypes.integer
        elif len(base_type_list) == 1:
            base_type = ctypes.simple_types[base_type_list[0]]
        else:
            descrip = "two or more data types in declaration specifiers"
            raise CompilerError(descrip, spec_range)

        signed_list = list({token_kinds.signed_kw, token_kinds.unsigned_kw} &
                            set(spec_kinds))

        if len(signed_list) == 1 and signed_list[0] == token_kinds.unsigned_kw:
            base_type = ctypes.to_unsigned(base_type)
        elif len(signed_list) > 1:
            descrip = "both signed and unsigned in declaration specifiers"
            raise CompilerError(descrip, spec_range)

        # Create set of storage class specifiers that are present
        storage_class_set = {token_kinds.auto_kw,
                             token_kinds.static_kw,
                             token_kinds.extern_kw}
        storage_class_single = storage_class_set & set(spec_kinds)

        if len(storage_class_single) == 0:
            storage = self.AUTO
        elif len(storage_class_single) == 1:
            if token_kinds.static_kw in storage_class_single:
                storage = self.STATIC
            elif token_kinds.extern_kw in storage_class_single:
                storage = self.EXTERN
            else:  # must be `auto` kw
                storage = self.AUTO
        else:
            descrip = "two or more storage classes in declaration specifiers"
            raise CompilerError(descrip, spec_range)

        return base_type, storage
