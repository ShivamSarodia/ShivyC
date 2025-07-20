"""Function call expression nodes in the AST."""

import shivyc.ctypes as ctypes
import shivyc.il_cmds.control as control_cmds
from shivyc.errors import CompilerError
from shivyc.il_gen import ILValue
from shivyc.tree.expr_base import _RExprNode
from shivyc.tree.utils import set_type, check_cast


class FuncCall(_RExprNode):
    """Function call.

    func - Expression of type function pointer
    args - List of expressions for each argument
    """
    def __init__(self, func, args):
        """Initialize node."""
        super().__init__()
        self.func = func
        self.args = args

    def make_il(self, il_code, symbol_table, c):
        """Make code for this node."""

        # This is of function pointer type, so func.arg is the function type.
        func = self.func.make_il(il_code, symbol_table, c)

        if not func.ctype.is_pointer() or not func.ctype.arg.is_function():
            descrip = "called object is not a function pointer"
            raise CompilerError(descrip, self.func.r)
        elif (func.ctype.arg.ret.is_incomplete()
              and not func.ctype.arg.ret.is_void()):
            # TODO: C11 spec says a function cannot return an array type,
            # but I can't determine how a function would ever be able to return
            # an array type.
            descrip = "function returns non-void incomplete type"
            raise CompilerError(descrip, self.func.r)

        if func.ctype.arg.no_info:
            final_args = self._get_args_without_prototype(
                il_code, symbol_table, c)
        else:
            final_args = self._get_args_with_prototype(
                func.ctype.arg, il_code, symbol_table, c)

        ret = ILValue(func.ctype.arg.ret)
        il_code.add(control_cmds.Call(func, final_args, ret))
        return ret

    def _get_args_without_prototype(self, il_code, symbol_table, c):
        """Return list of argument ILValues for function this represents.

        Use _get_args_without_prototype when the function this represents
        has no prototype. This function only performs integer promotion on the
        arguments before passing them to the called function.
        """
        final_args = []
        for arg_given in self.args:
            arg = arg_given.make_il(il_code, symbol_table, c)

            # perform integer promotions
            if arg.ctype.is_arith() and arg.ctype.size < 4:
                arg = set_type(arg, ctypes.integer, il_code)

            final_args.append(arg)
        return final_args

    def _get_args_with_prototype(self, func_ctype, il_code, symbol_table, c):
        """Return list of argument ILValues for function this represents.

        Use _get_args_with_prototype when the function this represents
        has a prototype. This function converts all passed arguments to
        expected types.
        """
        arg_types = func_ctype.args

        if len(arg_types) != len(self.args):
            err = ("incorrect number of arguments for function call"
                   f" (expected {len(arg_types)}, have {len(self.args)})")

            if self.args:
                raise CompilerError(err, self.args[-1].r)
            else:
                raise CompilerError(err, self.r)

        final_args = []
        for arg_given, arg_type in zip(self.args, arg_types):
            arg = arg_given.make_il(il_code, symbol_table, c)
            check_cast(arg, arg_type, arg_given.r)
            final_args.append(
                set_type(arg, arg_type.make_unqual(), il_code))
        return final_args
