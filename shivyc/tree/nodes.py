"""Nodes in the AST which represent statements or declarations."""

import shivyc.ctypes as ctypes
import shivyc.decl_tree as decl_tree
import shivyc.il_cmds.control as control_cmds
import shivyc.token_kinds as token_kinds

from shivyc.ctypes import PointerCType, ArrayCType, FunctionCType
from shivyc.errors import CompilerError
from shivyc.il_gen import ILValue
from shivyc.tree.utils import DirectLValue, report_err, set_type, check_cast


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
                err = "{} statement not in loop".format(self.descrip)
                raise CompilerError(err, self.r)


class Break(_BreakContinue):
    """Node for a break statement."""

    get_label = lambda _, c: c.break_label
    descrip = "break"


class Continue(_BreakContinue):
    """Node for a continue statement."""

    get_label = lambda _, c: c.continue_label
    descrip = "continue"


class EmptyStatement(Node):
    """Node for a statement which is just a semicolon."""

    def __init__(self):
        """Initialize node."""
        super().__init__()

    def make_il(self, il_code, symbol_table, c):
        """Nothing to do for a blank statement."""
        pass


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
        ctype, identifier, storage = self.make_ctype(
            decl, il_code, symbol_table)

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
            lval = DirectLValue(var)
            if lval.modable():
                lval.set_to(init_val, il_code, identifier.r)
            else:
                err = "declared variable is not of assignable type"
                raise CompilerError(err, decl.r)

    def make_ctype(self, decl, il_code, symbol_table,
                   prev_ctype=None, storage=0):
        """Generate a ctype from the given declaration.

        Return a `ctype, identifier token, storage class` triple.

        decl - Node of decl_tree to parse. See decl_tree.py for explanation
        about decl_trees.
        prev_ctype - The ctype formed from all parts of the tree above the
        current one.
        storage - The storage class of this declaration.
        """
        if isinstance(decl, decl_tree.Root):
            new_ctype, storage = self.make_specs_ctype(
                decl.specs, il_code, symbol_table)
        elif isinstance(decl, decl_tree.Pointer):
            new_ctype = PointerCType(prev_ctype)
        elif isinstance(decl, decl_tree.Array):
            new_ctype = ArrayCType(prev_ctype, decl.n)
        elif isinstance(decl, decl_tree.Function):
            # Create a new scope because if we create a new struct type inside
            # the function parameters, it should be local to those parameters.
            symbol_table.new_scope()
            args = [
                self.make_ctype(decl, il_code, symbol_table)[0]
                for decl in decl.args
            ]
            symbol_table.end_scope()
            new_ctype = FunctionCType(args, prev_ctype)
        elif isinstance(decl, decl_tree.Identifier):
            return prev_ctype, decl.identifier, storage

        return self.make_ctype(decl.child, il_code, symbol_table,
                               new_ctype, storage)

    def make_specs_ctype(self, specs, il_code, symbol_table):
        """Make a ctype out of the provided list of declaration specifiers.

        Return a `ctype, storage class` pair, where storage class is one of
        the above values.
        """
        spec_range = specs[0].r + specs[-1].r

        all_type_specs = (set(ctypes.simple_types) |
                          {token_kinds.signed_kw, token_kinds.unsigned_kw,
                           token_kinds.struct_kw})

        type_specs = [str(spec.kind) for spec in specs
                      if spec.kind in all_type_specs]
        specs_str = " ".join(sorted(type_specs))

        if specs_str == "struct":
            s = [s for s in specs if s.kind == token_kinds.struct_kw][0]
            base_type = self.parse_struct_spec(s, il_code, symbol_table)
        else:
            base_type = self.get_base_ctype(specs_str, spec_range)

        storage = self.get_storage([spec.kind for spec in specs], spec_range)
        return base_type, storage

    def get_base_ctype(self, specs_str, spec_range):
        """Return a ctype given a sorted space-separated specifier string."""

        # replace "long long" with "long" for convenience
        specs_str = specs_str.replace("long long", "long")

        specs = {
            "void": ctypes.void,

            "_Bool": ctypes.bool_t,

            "char": ctypes.char,
            "char signed": ctypes.char,
            "char unsigned": ctypes.unsig_char,

            "short": ctypes.short,
            "short signed": ctypes.short,
            "int short": ctypes.short,
            "int short signed": ctypes.short,
            "short unsigned": ctypes.unsig_short,
            "int short unsigned": ctypes.unsig_short,

            "int": ctypes.integer,
            "signed": ctypes.integer,
            "int signed": ctypes.integer,
            "unsigned": ctypes.unsig_int,
            "int unsigned": ctypes.unsig_int,

            "long": ctypes.longint,
            "long signed": ctypes.longint,
            "int long": ctypes.longint,
            "int long signed": ctypes.longint,
            "long unsigned": ctypes.unsig_longint,
            "int long unsigned": ctypes.unsig_longint,
        }

        if specs_str in specs:
            return specs[specs_str]

        # TODO: provide more helpful feedback on what is wrong
        descrip = "unrecognized set of type specifiers"
        raise CompilerError(descrip, spec_range)

    def get_storage(self, spec_kinds, spec_range):
        """Return the storage class from given specifier token kinds."""

        storage_classes = {token_kinds.auto_kw: self.AUTO,
                           token_kinds.static_kw: self.STATIC,
                           token_kinds.extern_kw: self.EXTERN}

        storage = None
        for kind in spec_kinds:
            if kind in storage_classes and not storage:
                storage = storage_classes[kind]
            elif kind in storage_classes:
                descrip = "too many storage classes in declaration specifiers"
                raise CompilerError(descrip, spec_range)

        return storage if storage else self.AUTO

    def parse_struct_spec(self, spec, redec, il_code, symbol_table):
        """Parse a struct ctype from the given decl_tree.Struct node.

        spec (decl_tree.Struct) - the Struct node to parse
        redec (bool) - Whether this declaration is alone like so:

           struct S;

        or declares variables/has storage specifiers:

           struct S *p;
           extern struct S;

        If it's the first, then this is always a forward declaration for a
        new `struct S` but if it's the second and a `struct S` already
        exists in higher scope, it's just using the higher scope struct.
        """

        # symbol table functions
        # lookup_struct()
        #  - looks up and returns struct with given tag
        #  - return peacefully if not found
        # add_struct(tag, struct)
        #  - if an struct with the same tag already exists at topmost
        #    scope, does nothing
        #  - otherwise, adds an incomplete struct with this tag to topmost
        #    scope
        # complete_struct()
        #  - searches for struct with same tag at topmost scope
        #  - if none exists, error (idk if this will ever happen)
        #  - if one does exist, and it's complete, error
        #  - if one does exist, and it's incomplete, then complete it

        # if spec.tag:
        #   this_struct = lookup_struct()
        #   if not this_struct or spec.members or redec:
        #       this_struct = add_struct(tag, incomplete-struct)
        # if not spec.tag:
        #   this_struct = StructCType(tag is None)

        # if spec.members:
        #   for each member, make a ctype out of it, then figure out if it
        #    includes something it shouldn't (array, incomp type, typedef,
        #    extern)
        #   this_struct.complete()

        # return this_struct

        # ALSO rn creating a new struct type with no actual variables
        # doesn't even create a new type, so fix that!

        # ^^^ actually this is an even more fundamental issue. RN, I just
        # copy the specs to each and every declarator in a single
        # declaration. But that's not okay because if the specs are a
        # struct, then each time you parse the specs, you generate a new
        # struct object. Yikes. This is even an issue for struct members,
        # because somewhere I do some sketchy merging of lists for getting
        # a convenient list but this removes information on the distinct specs.

        raise NotImplementedError
