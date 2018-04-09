"""Nodes in the AST which represent statements or declarations."""

import shivyc.ctypes as ctypes
import shivyc.il_cmds.control as control_cmds
import shivyc.il_cmds.value as value_cmds
import shivyc.token_kinds as token_kinds
import shivyc.tree.decl_nodes as decl_nodes
from shivyc.ctypes import PointerCType, ArrayCType, FunctionCType, StructCType
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


class Compound(Node):
    """Node for a compound statement."""

    def __init__(self, items):
        """Initialize node."""
        super().__init__()
        self.items = items

    def make_il(self, il_code, symbol_table, c, no_scope=False):
        """Make IL code for every block item, in order.

        If no_scope is True, then do not create a new symbol table scope.
        Used by function definition so that parameters can live in the scope
        of the function body.
        """
        if not no_scope:
            symbol_table.new_scope()

        c = c.set_global(False)
        for item in self.items:
            with report_err():
                item.make_il(il_code, symbol_table, c)

        if not no_scope:
            symbol_table.end_scope()


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


class DeclInfo:
    """Contains information about the declaration of one identifier.

    identifier - the identifier being declared
    ctype - the ctype of this identifier
    storage - the storage class of this identifier
    init - the initial value of this identifier
    """

    # Storage class specifiers for declarations
    AUTO = 1
    STATIC = 2
    EXTERN = 3

    def __init__(self, identifier, ctype, range,
                 storage=None, init=None, body=None, param_names=None):
        self.identifier = identifier
        self.ctype = ctype
        self.range = range
        self.storage = storage
        self.init = init
        self.body = body
        self.param_names = param_names

    def process(self, il_code, symbol_table, c):
        """Process given DeclInfo object.

        This includes error checking, adding the variable to the symbol
        table, and registering it with the IL.
        """
        if not self.identifier:
            err = "missing identifier name in declaration"
            raise CompilerError(err, self.range)

        if self.ctype.is_incomplete():
            err = "variable of incomplete type declared"
            raise CompilerError(err, self.range)

        if self.body and not self.ctype.is_function():
            err = "function definition provided for non-function type"
            raise CompilerError(err, self.range)

        linkage = self.get_linkage(symbol_table, c)

        if not c.is_global and self.init and linkage:
            err = "variable with linkage has initializer"
            raise CompilerError(err, self.range)

        defined = self.get_defined()

        var = symbol_table.add(
            self.identifier,
            self.ctype,
            defined,
            linkage)

        storage = self.get_storage(defined, linkage, il_code)

        if storage == il_code.STATIC and self.init:
            raise NotImplementedError(
                "initializer on static storage unsupported")

        name = self.identifier.content
        il_code.register_storage(var, storage, name)
        if linkage == symbol_table.EXTERNAL:
            il_code.register_extern_linkage(var, name)
        if defined:
            il_code.register_defined(var, name)

        if self.init:
            self.do_init(var, il_code, symbol_table, c)
        if self.body:
            self.do_body(il_code, symbol_table, c)

    def do_init(self, var, il_code, symbol_table, c):
        """Create code for initializing given variable.

        Caller must check that this object has an initializer.
        """
        init_val = self.init.make_il(il_code, symbol_table, c)
        lval = DirectLValue(var)

        if lval.ctype().is_arith() or lval.ctype().is_pointer():
            lval.set_to(init_val, il_code, self.identifier.r)
        else:
            err = "declared variable is not of assignable type"
            raise CompilerError(err, self.range)

    def do_body(self, il_code, symbol_table, c):
        """Create code for function body.

        Caller must check that this function has a body.
        """
        is_main = self.identifier.content == "main"

        for param in self.param_names:
            if not param:
                err = "function definition missing parameter name"
                raise CompilerError(err, self.range)

        if is_main:
            self.check_main_type()

        c = c.set_return(self.ctype.ret)
        il_code.start_func(self.identifier.content)

        symbol_table.new_scope()

        num_params = len(self.ctype.args)
        iter = zip(self.ctype.args, self.param_names, range(num_params))
        for ctype, param, i in iter:
            arg = symbol_table.add(param, ctype, True, None)
            il_code.add(value_cmds.LoadArg(arg, i))

        self.body.make_il(il_code, symbol_table, c, no_scope=True)
        if not il_code.always_returns() and is_main:
            zero = ILValue(ctypes.integer)
            il_code.register_literal_var(zero, 0)
            il_code.add(control_cmds.Return(zero))
        elif not il_code.always_returns():
            il_code.add(control_cmds.Return(None))

        symbol_table.end_scope()

    def check_main_type(self):
        """Check if function signature matches signature expected of main.

        Raises an exception if this function signature does not match the
        function signature expected of the main function.
        """
        if not self.ctype.ret.compatible(ctypes.integer):
            err = "'main' function must have integer return type"
            raise CompilerError(err, self.range)
        if len(self.ctype.args) not in {0, 2}:
            err = "'main' function must have 0 or 2 arguments"
            raise CompilerError(err, self.range)
        if self.ctype.args:
            first = self.ctype.args[0]
            second = self.ctype.args[1]

            if not first.compatible(ctypes.integer):
                err = "first parameter of 'main' must be of integer type"
                raise CompilerError(err, self.range)

            is_ptr_array = second.arg.is_pointer() or second.arg.is_array()
            if (not second.is_pointer() or not is_ptr_array
                    or not second.arg.arg.compatible(ctypes.char)):
                err = "second parameter of 'main' must be like char**"
                raise CompilerError(err, self.range)

    def get_linkage(self, symbol_table, c):
        """Get linkage type for given decl_info object.

        See 6.2.2 in the C11 spec for details.
        """
        if c.is_global and self.storage == DeclInfo.STATIC:
            linkage = symbol_table.INTERNAL
        elif self.storage == DeclInfo.EXTERN:
            var = symbol_table.lookup_raw(self.identifier.content)
            if var and var.linkage:
                linkage = var.linkage
            else:
                linkage = symbol_table.EXTERNAL
        elif self.ctype.is_function() and not self.storage:
            linkage = symbol_table.EXTERNAL
        elif c.is_global and not self.storage:
            linkage = symbol_table.EXTERNAL
        else:
            linkage = None

        return linkage

    def get_defined(self):
        """Determine whether this is a definition."""
        if self.storage == self.EXTERN and not (self.init or self.body):
            return False
        elif self.ctype.is_function() and not self.body:
            return False
        else:
            return True

    def get_storage(self, defined, linkage, il_code):
        """Determine the storage duration."""
        if not defined or not self.ctype.is_object():
            storage = None
        elif linkage or self.storage == self.STATIC:
            storage = il_code.STATIC
        else:
            storage = il_code.AUTOMATIC

        return storage


class Declaration(Node):
    """Line of a general variable declaration(s).

    node (decl_nodes.Root) - a declaration tree for this line
    body (Compound(Node)) - if this is a function definition, the body of
    the function
    """

    def __init__(self, node, body=None):
        """Initialize node."""
        super().__init__()
        self.node = node
        self.body = body

    def make_il(self, il_code, symbol_table, c):
        """Make code for this declaration."""

        decl_infos = self.get_decl_infos(self.node, symbol_table)
        for info in decl_infos:
            with report_err():
                info.process(il_code, symbol_table, c)

    def get_decl_infos(self, node, symbol_table):
        """Given a node, returns a list of decl_info objects for that node."""
        any_dec = bool(node.decls)
        base_type, storage = self.make_specs_ctype(
            node.specs, any_dec, symbol_table)

        proc = zip(node.decls, node.ranges, node.inits)

        out = []
        for decl, range, init in proc:
            with report_err():
                ctype, identifier = self.make_ctype(
                    decl, base_type, symbol_table)

                if isinstance(decl, decl_nodes.Function):
                    param_names = [
                        self.get_decl_infos(param, symbol_table)[0].identifier
                        for param in decl.args]
                else:
                    param_names = []

                out.append(DeclInfo(
                    identifier, ctype, range, storage, init,
                    self.body, param_names))

        return out

    def make_ctype(self, decl, prev_ctype, symbol_table):
        """Generate a ctype from the given declaration.

        Return a `ctype, identifier token` tuple.

        decl - Node of decl_nodes to parse. See decl_nodes.py for explanation
        about decl_nodes.
        prev_ctype - The ctype formed from all parts of the tree above the
        current one.
        """
        if isinstance(decl, decl_nodes.Pointer):
            new_ctype = PointerCType(prev_ctype, decl.const)
        elif isinstance(decl, decl_nodes.Array):
            new_ctype = ArrayCType(prev_ctype, decl.n)
        elif isinstance(decl, decl_nodes.Function):
            # Prohibit storage class specifiers in parameters.
            for param in decl.args:
                decl_info = self.get_decl_infos(param, symbol_table)[0]
                if decl_info.storage:
                    err = "storage class specified for function parameter"
                    raise CompilerError(err, decl_info.range)

            # Create a new scope because if we create a new struct type inside
            # the function parameters, it should be local to those parameters.
            symbol_table.new_scope()
            args = [
                self.get_decl_infos(decl, symbol_table)[0].ctype
                for decl in decl.args
            ]
            symbol_table.end_scope()

            # adjust array and function parameters
            has_void = False
            for i in range(len(args)):
                ctype = args[i]
                if ctype.is_array():
                    args[i] = PointerCType(ctype.el)
                elif ctype.is_function():
                    args[i] = PointerCType(ctype)
                elif ctype.is_void():
                    has_void = True

            if has_void and len(args) > 1:
                decl_info = self.get_decl_infos(decl.args[0], symbol_table)[0]
                err = "'void' must be the only parameter"
                raise CompilerError(err, decl_info.range)

            # Function declarators cannot have a function or array return type.
            # TODO: Relevant only when typedef is implemented.

            if not args and not self.body:
                new_ctype = FunctionCType([], prev_ctype, True)
            elif has_void:
                new_ctype = FunctionCType([], prev_ctype, False)
            else:
                new_ctype = FunctionCType(args, prev_ctype, False)

        elif isinstance(decl, decl_nodes.Identifier):
            return prev_ctype, decl.identifier

        return self.make_ctype(decl.child, new_ctype, symbol_table)

    def make_specs_ctype(self, specs, any_dec, symbol_table):
        """Make a ctype out of the provided list of declaration specifiers.

        any_dec - Whether these specifiers are used to declare a variable.
        This value is important because `struct A;` has a different meaning
        than `struct A *p;`, since the former forward-declares a new struct
        while the latter may reuse a struct A that already exists in scope.

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

        storage = self.get_storage([spec.kind for spec in specs], spec_range)

        const = token_kinds.const_kw in {spec.kind for spec in specs}

        if specs_str == "struct":
            s = [s for s in specs if s.kind == token_kinds.struct_kw][0]

            # This is a redeclaration of a struct if there are no storage
            # specifiers and it declares no variables.
            redec = not any_dec and storage is None
            base_type = self.parse_struct_spec(s, redec, symbol_table)
            if const: base_type = base_type.make_const()
        else:
            base_type = self.get_base_ctype(specs_str, spec_range, const)

        return base_type, storage

    def get_base_ctype(self, specs_str, spec_range, const):
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
            ctype = specs[specs_str]
            return ctype.make_const() if const else ctype

        # TODO: provide more helpful feedback on what is wrong
        descrip = "unrecognized set of type specifiers"
        raise CompilerError(descrip, spec_range)

    def get_storage(self, spec_kinds, spec_range):
        """Determine the storage class from given specifier token kinds.

        If no storage class is listed, returns None.
        """
        storage_classes = {token_kinds.auto_kw: DeclInfo.AUTO,
                           token_kinds.static_kw: DeclInfo.STATIC,
                           token_kinds.extern_kw: DeclInfo.EXTERN}

        storage = None
        for kind in spec_kinds:
            if kind in storage_classes and not storage:
                storage = storage_classes[kind]
            elif kind in storage_classes:
                descrip = "too many storage classes in declaration specifiers"
                raise CompilerError(descrip, spec_range)

        return storage

    def parse_struct_spec(self, node, redec, symbol_table):
        """Parse a struct ctype from the given decl_nodes.Struct node.

        node (decl_nodes.Struct) - the Struct node to parse
        redec (bool) - Whether this declaration is alone like so:

           struct S;

        or declares variables/has storage specifiers:

           struct S *p;
           extern struct S;

        If it's the first, then this is always a forward declaration for a
        new `struct S` but if it's the second and a `struct S` already
        exists in higher scope, it's just using the higher scope struct.
        """
        has_members = node.members is not None
        if node.tag:
            tag = str(node.tag)
            ctype = symbol_table.lookup_struct(tag)

            if not ctype or has_members or redec:
                ctype = symbol_table.add_struct(tag, StructCType(tag))

            if has_members and ctype.is_complete():
                err = f"redefinition of 'struct {tag}'"
                raise CompilerError(err, node.r)

        else:
            ctype = StructCType(None)

        if not has_members:
            return ctype

        # Struct does have members
        members = []
        member_set = set()
        for member in node.members:
            decl_infos = []  # needed in case get_decl_infos below fails
            with report_err():
                decl_infos = self.get_decl_infos(member, symbol_table)

            for decl_info in decl_infos:
                with report_err():
                    if decl_info.identifier is None:
                        # someone snuck an abstract declarator into here!
                        err = "missing name of struct member"
                        raise CompilerError(err, decl_info.range)

                    if decl_info.storage is not None:
                        err = "cannot have storage specifier on struct member"
                        raise CompilerError(err, decl_info.range)

                    if decl_info.ctype.is_function():
                        err = "cannot have function type as struct member"
                        raise CompilerError(err, decl_info.range)

                    # TODO: 6.7.2.1.18 (allow flexible array members)
                    if decl_info.ctype.is_incomplete():
                        err = "cannot have incomplete type as struct member"
                        raise CompilerError(err, decl_info.range)

                    # TODO: 6.7.2.1.13 (anonymous structs)
                    attr = decl_info.identifier.content

                    if attr in member_set:
                        err = f"duplicate member '{attr}'"
                        raise CompilerError(err, decl_info.identifier.r)

                    members.append((attr, decl_info.ctype))
                    member_set.add(attr)

        ctype.set_members(members)
        return ctype
