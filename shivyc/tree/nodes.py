"""Nodes in the AST which represent statements or declarations."""

import shivyc.ctypes as ctypes
import shivyc.il_cmds.control as control_cmds
import shivyc.il_cmds.value as value_cmds
import shivyc.token_kinds as token_kinds
import shivyc.tree.decl_nodes as decl_nodes
from shivyc.ctypes import (PointerCType, ArrayCType, FunctionCType,
                           StructCType, UnionCType)
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
    TYPEDEF = 4

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

        # The typedef is special
        if self.storage == self.TYPEDEF:
            self.process_typedef(symbol_table)
            return

        if self.body and not self.ctype.is_function():
            err = "function definition provided for non-function type"
            raise CompilerError(err, self.range)

        linkage = self.get_linkage(symbol_table, c)
        defined = self.get_defined(symbol_table, c)
        storage = self.get_storage(defined, linkage, symbol_table)

        if not c.is_global and self.init and linkage:
            err = "local variable with linkage has initializer"
            raise CompilerError(err, self.range)

        var = symbol_table.add_variable(
            self.identifier,
            self.ctype,
            defined,
            linkage,
            storage)

        if self.init:
            self.do_init(var, storage, il_code, symbol_table, c)
        if self.body:
            self.do_body(il_code, symbol_table, c)

        if not linkage and self.ctype.is_incomplete():
            err = "variable of incomplete type declared"
            raise CompilerError(err, self.range)

    def process_typedef(self, symbol_table):
        """Process type declarations."""

        if self.init:
            err = "typedef cannot have initializer"
            raise CompilerError(err, self.range)

        if self.body:
            err = "function definition cannot be a typedef"
            raise CompilerError(err, self.range)

        symbol_table.add_typedef(self.identifier, self.ctype)

    def do_init(self, var, storage, il_code, symbol_table, c):
        """Create code for initializing given variable.

        Caller must check that this object has an initializer.
        """
        # little bit hacky, but will be fixed when full initializers are
        # implemented shortly

        init = self.init.make_il(il_code, symbol_table, c)
        if storage == symbol_table.STATIC and not init.literal:
            err = ("non-constant initializer for variable with static "
                   "storage duration")
            raise CompilerError(err, self.init.r)
        elif storage == symbol_table.STATIC:
            il_code.static_initialize(var, getattr(init.literal, "val", None))
        elif var.ctype.is_arith() or var.ctype.is_pointer():
            lval = DirectLValue(var)
            lval.set_to(init, il_code, self.identifier.r)
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
            arg = symbol_table.add_variable(
                param, ctype, symbol_table.DEFINED, None,
                symbol_table.AUTOMATIC)
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

            is_ptr_array = (second.is_pointer() and
                            (second.arg.is_pointer() or second.arg.is_array()))

            if not is_ptr_array or not second.arg.arg.compatible(ctypes.char):
                err = "second parameter of 'main' must be like char**"
                raise CompilerError(err, self.range)

    def get_linkage(self, symbol_table, c):
        """Get linkage type for given decl_info object.

        See 6.2.2 in the C11 spec for details.
        """
        if c.is_global and self.storage == DeclInfo.STATIC:
            linkage = symbol_table.INTERNAL
        elif self.storage == DeclInfo.EXTERN:
            cur_linkage = symbol_table.lookup_linkage(self.identifier)
            linkage = cur_linkage or symbol_table.EXTERNAL
        elif self.ctype.is_function() and not self.storage:
            linkage = symbol_table.EXTERNAL
        elif c.is_global and not self.storage:
            linkage = symbol_table.EXTERNAL
        else:
            linkage = None

        return linkage

    def get_defined(self, symbol_table, c):
        """Determine whether this is a definition."""
        if (c.is_global and self.storage in {None, self.STATIC}
              and self.ctype.is_object() and not self.init):
            return symbol_table.TENTATIVE
        elif self.storage == self.EXTERN and not (self.init or self.body):
            return symbol_table.UNDEFINED
        elif self.ctype.is_function() and not self.body:
            return symbol_table.UNDEFINED
        else:
            return symbol_table.DEFINED

    def get_storage(self, defined, linkage, symbol_table):
        """Determine the storage duration."""
        if defined == symbol_table.UNDEFINED or not self.ctype.is_object():
            storage = None
        elif linkage or self.storage == self.STATIC:
            storage = symbol_table.STATIC
        else:
            storage = symbol_table.AUTOMATIC

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

        self.set_self_vars(il_code, symbol_table, c)
        decl_infos = self.get_decl_infos(self.node)
        for info in decl_infos:
            with report_err():
                info.process(il_code, symbol_table, c)

    def set_self_vars(self, il_code, symbol_table, c):
        """Set il_code, symbol_table, and context as attributes of self.

        Helper function to prevent us from having to pass these three
        arguments into almost all functions in this class.

        """
        self.il_code = il_code
        self.symbol_table = symbol_table
        self.c = c

    def get_decl_infos(self, node):
        """Given a node, returns a list of decl_info objects for that node."""

        any_dec = bool(node.decls)
        base_type, storage = self.make_specs_ctype(node.specs, any_dec)

        out = []
        for decl, init in zip(node.decls, node.inits):
            with report_err():
                ctype, identifier = self.make_ctype(decl, base_type)

                if ctype.is_function():
                    param_identifiers = self.extract_params(decl)
                else:
                    param_identifiers = []

                out.append(DeclInfo(
                    identifier, ctype, decl.r, storage, init,
                    self.body, param_identifiers))

        return out

    def make_ctype(self, decl, prev_ctype):
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
            new_ctype = self._generate_array_ctype(decl, prev_ctype)
        elif isinstance(decl, decl_nodes.Function):
            new_ctype = self._generate_func_ctype(decl, prev_ctype)
        elif isinstance(decl, decl_nodes.Identifier):
            return prev_ctype, decl.identifier

        return self.make_ctype(decl.child, new_ctype)

    def _generate_array_ctype(self, decl, prev_ctype):
        """Generate a function ctype from a given a decl_node."""

        if decl.n:
            il_value = decl.n.make_il(self.il_code, self.symbol_table, self.c)
            if not il_value.ctype.is_integral():
                err = "array size must have integral type"
                raise CompilerError(err, decl.r)
            if not il_value.literal:
                err = "array size must be compile-time constant"
                raise CompilerError(err, decl.r)
            if il_value.literal.val <= 0:
                err = "array size must be positive"
                raise CompilerError(err, decl.r)
            if not prev_ctype.is_complete():
                err = "array elements must have complete type"
                raise CompilerError(err, decl.r)
            return ArrayCType(prev_ctype, il_value.literal.val)
        else:
            return ArrayCType(prev_ctype, None)

    def _generate_func_ctype(self, decl, prev_ctype):
        """Generate a function ctype from a given a decl_node."""

        # Prohibit storage class specifiers in parameters.
        for param in decl.args:
            decl_info = self.get_decl_infos(param)[0]
            if decl_info.storage:
                err = "storage class specified for function parameter"
                raise CompilerError(err, decl_info.range)

        # Create a new scope because if we create a new struct type inside
        # the function parameters, it should be local to those parameters.
        self.symbol_table.new_scope()
        args = [
            self.get_decl_infos(decl)[0].ctype
            for decl in decl.args
        ]
        self.symbol_table.end_scope()

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
            decl_info = self.get_decl_infos(decl.args[0])[0]
            err = "'void' must be the only parameter"
            raise CompilerError(err, decl_info.range)
        if prev_ctype.is_function():
            err = "function cannot return function type"
            raise CompilerError(err, self.r)
        if prev_ctype.is_array():
            err = "function cannot return array type"
            raise CompilerError(err, self.r)

        if not args and not self.body:
            new_ctype = FunctionCType([], prev_ctype, True)
        elif has_void:
            new_ctype = FunctionCType([], prev_ctype, False)
        else:
            new_ctype = FunctionCType(args, prev_ctype, False)
        return new_ctype

    def extract_params(self, decl):
        """Return the parameter list for this function."""

        identifiers = []
        func_decl = None
        while decl and not isinstance(decl, decl_nodes.Identifier):
            if isinstance(decl, decl_nodes.Function):
                func_decl = decl
            decl = decl.child

        if not func_decl:
            # This condition is true for the following code:
            #
            # typedef int F(void);
            # F f { }
            #
            # See 6.9.1.2
            err = "function definition missing parameter list"
            raise CompilerError(err, self.r)

        for param in func_decl.args:
            decl_info = self.get_decl_infos(param)[0]
            identifiers.append(decl_info.identifier)

        return identifiers

    def make_specs_ctype(self, specs, any_dec):
        """Make a ctype out of the provided list of declaration specifiers.

        any_dec - Whether these specifiers are used to declare a variable.
        This value is important because `struct A;` has a different meaning
        than `struct A *p;`, since the former forward-declares a new struct
        while the latter may reuse a struct A that already exists in scope.

        Return a `ctype, storage class` pair, where storage class is one of
        the above values.
        """
        spec_range = specs[0].r + specs[-1].r
        storage = self.get_storage([spec.kind for spec in specs], spec_range)
        const = token_kinds.const_kw in {spec.kind for spec in specs}

        struct_union_specs = {token_kinds.struct_kw, token_kinds.union_kw}
        if any(s.kind in struct_union_specs for s in specs):
            node = [s for s in specs if s.kind in struct_union_specs][0]

            # This is a redeclaration of a struct if there are no storage
            # specifiers and it declares no variables.
            redec = not any_dec and storage is None
            base_type = self.parse_struct_union_spec(node, redec)

        # is a typedef
        elif any(s.kind == token_kinds.identifier for s in specs):
            ident = [s for s in specs if s.kind == token_kinds.identifier][0]
            base_type = self.symbol_table.lookup_typedef(ident)

        else:
            base_type = self.get_base_ctype(specs, spec_range)

        if const: base_type = base_type.make_const()
        return base_type, storage

    def get_base_ctype(self, specs, spec_range):
        """Return a base ctype given a list of specs."""

        base_specs = set(ctypes.simple_types)
        base_specs |= {token_kinds.signed_kw, token_kinds.unsigned_kw}

        our_base_specs = [str(spec.kind) for spec in specs
                          if spec.kind in base_specs]
        specs_str = " ".join(sorted(our_base_specs))

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
        """Determine the storage class from given specifier token kinds.

        If no storage class is listed, returns None.
        """
        storage_classes = {token_kinds.auto_kw: DeclInfo.AUTO,
                           token_kinds.static_kw: DeclInfo.STATIC,
                           token_kinds.extern_kw: DeclInfo.EXTERN,
                           token_kinds.typedef_kw: DeclInfo.TYPEDEF}

        storage = None
        for kind in spec_kinds:
            if kind in storage_classes and not storage:
                storage = storage_classes[kind]
            elif kind in storage_classes:
                descrip = "too many storage classes in declaration specifiers"
                raise CompilerError(descrip, spec_range)

        return storage

    def parse_struct_union_spec(self, node, redec):
        """Parse struct or union ctype from the given decl_nodes.Struct node.

        node (decl_nodes.Struct/Union) - the Struct or Union node to parse
        redec (bool) - Whether this declaration is alone like so:

           struct S;
           union U;

        or declares variables/has storage specifiers:

           struct S *p;
           extern struct S;
           union U *u;
           extern union U;

        If it's the first, then this is always a forward declaration for a
        new `struct S` but if it's the second and a `struct S` already
        exists in higher scope, it's just using the higher scope struct.
        """
        has_members = node.members is not None

        if node.kind == token_kinds.struct_kw:
            ctype_req = StructCType
        else:
            ctype_req = UnionCType

        if node.tag:
            tag = str(node.tag)
            ctype = self.symbol_table.lookup_struct_union(tag)

            if ctype and not isinstance(ctype, ctype_req):
                err = f"defined as wrong kind of tag '{node.kind} {tag}'"
                raise CompilerError(err, node.r)

            if not ctype or has_members or redec:
                ctype = self.symbol_table.add_struct_union(tag, ctype_req(tag))

            if has_members and ctype.is_complete():
                err = f"redefinition of '{node.kind} {tag}'"
                raise CompilerError(err, node.r)

        else:  # anonymous struct/union
            ctype = ctype_req(None)

        if not has_members:
            return ctype

        # Struct or union does have members
        members = []
        members_set = set()
        for member in node.members:
            decl_infos = []  # needed in case get_decl_infos below fails
            with report_err():
                decl_infos = self.get_decl_infos(member)

            for decl_info in decl_infos:
                with report_err():
                    self._check_struct_member_decl_info(
                        decl_info, node.kind, members_set)

                    name = decl_info.identifier.content
                    members_set.add(name)
                    members.append((name, decl_info.ctype))

        ctype.set_members(members)
        return ctype

    def _check_struct_member_decl_info(self, decl_info, kind, members):
        """Check whether given decl_info object is a valid struct member."""

        if decl_info.identifier is None:
            # someone snuck an abstract declarator into here!
            err = f"missing name of {kind} member"
            raise CompilerError(err, decl_info.range)

        if decl_info.storage is not None:
            err = f"cannot have storage specifier on {kind} member"
            raise CompilerError(err, decl_info.range)

        if decl_info.ctype.is_function():
            err = f"cannot have function type as {kind} member"
            raise CompilerError(err, decl_info.range)

        # TODO: 6.7.2.1.18 (allow flexible array members)
        if not decl_info.ctype.is_complete():
            err = f"cannot have incomplete type as {kind} member"
            raise CompilerError(err, decl_info.range)

        # TODO: 6.7.2.1.13 (anonymous structs)
        if decl_info.identifier.content in members:
            err = f"duplicate member '{decl_info.identifier.content}'"
            raise CompilerError(err, decl_info.identifier.r)
