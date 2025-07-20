"""Type operation expression nodes in the AST."""

import shivyc.ctypes as ctypes
from shivyc.errors import CompilerError
from shivyc.il_gen import ILValue
from shivyc.tree.expr_base import _RExprNode
from shivyc.tree.general_nodes import Declaration
from shivyc.tree.utils import set_type


class _SizeofNode(_RExprNode):
    """Base class for common logic for the two sizeof nodes."""

    def __init__(self):
        super().__init__()

    def sizeof_ctype(self, ctype, range, il_code):
        """Raise CompilerError if ctype is not valid as sizeof argument."""

        if ctype.is_function():
            err = "sizeof argument cannot have function type"
            raise CompilerError(err, range)

        if ctype.is_incomplete():
            err = "sizeof argument cannot have incomplete type"
            raise CompilerError(err, range)

        out = ILValue(ctypes.unsig_longint)
        il_code.register_literal_var(out, ctype.size)
        return out


class SizeofExpr(_SizeofNode):
    """Node representing sizeof with expression operand.

    expr (_ExprNode) - the expression to get the size of
    """
    def __init__(self, expr):
        super().__init__()
        self.expr = expr

    def make_il(self, il_code, symbol_table, c):
        """Return a compile-time integer literal as the expression size."""

        dummy_il_code = il_code.copy()
        expr = self.expr.make_il_raw(dummy_il_code, symbol_table, c)
        return self.sizeof_ctype(expr.ctype, self.expr.r, il_code)


class SizeofType(_SizeofNode, Declaration):
    """Node representing sizeof with abstract type as operand.

    node (decl_nodes.Root) - a declaration tree for the type
    """
    def __init__(self, node):
        _SizeofNode.__init__(self)
        Declaration.__init__(self, node)   # sets self.node = node

    def make_il(self, il_code, symbol_table, c):
        """Return a compile-time integer literal as the expression size."""

        self.set_self_vars(il_code, symbol_table, c)
        base_type, _ = self.make_specs_ctype(self.node.specs, False)
        ctype, _ = self.make_ctype(self.node.decls[0], base_type)
        return self.sizeof_ctype(ctype, self.node.decls[0].r, il_code)


class Cast(Declaration, _RExprNode):
    """Node representing a cast operation, like `(void*)p`.

    node (decl_nodes.Root) - a declaration tree for this line

    TODO: Share code between Cast and Declaration nodes more cleanly.
    """
    def __init__(self, node, expr):
        Declaration.__init__(self, node)   # sets self.node = node
        _RExprNode.__init__(self)

        self.expr = expr

    def make_il(self, il_code, symbol_table, c):
        """Make IL for this cast operation."""

        self.set_self_vars(il_code, symbol_table, c)
        base_type, _ = self.make_specs_ctype(self.node.specs, False)
        ctype, _ = self.make_ctype(self.node.decls[0], base_type)

        if not ctype.is_void() and not ctype.is_scalar():
            err = "can only cast to scalar or void type"
            raise CompilerError(err, self.node.decls[0].r)

        il_value = self.expr.make_il(il_code, symbol_table, c)
        if not il_value.ctype.is_scalar():
            err = "can only cast from scalar type"
            raise CompilerError(err, self.r)

        return set_type(il_value, ctype, il_code)
