"""Classes for the nodes that form our abstract syntax tree (AST).

Each node corresponds to a rule in the C grammar and has a make_code function
that generates code in our three-address IL.

"""

import ctypes
import token_kinds
import il_commands
from errors import CompilerError, error_collector
from il_gen import CType, ILValue, ILCode, LValue, check_cast, set_type
from il_gen import PointerCType, FunctionCType
from tokens import Token


class Node:
    """General class for representing a single node in the AST.

    Inherit all AST nodes from this class. Every AST node also has a make_code
    function that accepts a il_code (ILCode) to which the generated IL code
    should be saved.

    symbol (enum) - Non-terminal symbol the rule corresponding to a node
    produces. This value is checked by parent nodes to make sure the children
    produce symbols of the expected type.

    """

    # Enum for symbols produced by a node
    MAIN_FUNCTION = 1
    STATEMENT = 2
    DECLARATION = 3
    EXPRESSION = 4

    def __eq__(self, other):
        """Check whether all children of this node are equal."""
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False  # pragma: no cover

    def assert_symbol(self, node, symbol_name):
        """Check whether the provided node is of the given symbol.

        Useful for enforcing tree structure. Raises an exception if the node
        represents a rule that does not produce the expected symbol.

        """
        if node.symbol != symbol_name:
            raise ValueError("malformed tree: expected symbol '" +
                             str(symbol_name) + "' but got '" +
                             str(node.symbol) + "'")  # pragma: no cover

    def assert_symbols(self, node, symbol_names):
        """Check whether the provided node is one of the given symbols.

        Useful for enforcing tree structure. Raises an exception if the node
        represents a rule that produces none of the symbols in symbol_names.

        """
        if node.symbol not in symbol_names:
            raise ValueError("malformed tree: unexpected symbol '" +
                             str(node.symbol) + "'")  # pragma: no cover

    def assert_kind(self, token, kind):
        """Check whether the provided token is of the given token kind.

        Useful for enforcing tree structure. Raises an exception if the token
        does not have the given kind.

        """
        if token.kind != kind:
            raise ValueError("malformed tree: expected token_kind '" +
                             str(kind) + "' but got '" +
                             str(token.kind) + "'")  # pragma: no cover

    def make_code(self, il_code, symbol_table):
        """Make code for this node.

        Add IL code for this node to the given il_code object.
        """
        raise NotImplementedError


class ExpressionNode(Node):
    """General class for representing an expression node in the AST.

    Subclasses should implement the make_code_raw function.

    """

    symbol = Node.EXPRESSION

    def make_code(self, il_code, symbol_table):
        """Make code for this node and return decayed version of result."""
        return self._decay(self.make_code_raw(il_code, symbol_table), il_code)

    def _decay(self, il_value, il_code):
        """Decay given ILValue if needed.

        If given ILValue is of function type or array type, decays it into a
        pointer and emits code necessary to do so.
        """
        if il_value.ctype.type_type == CType.ARRAY:
            new_type = PointerCType(il_value.ctype.el)
            out = ILValue(new_type)
            il_code.add(il_commands.AddrOf(out, il_value))
            return out
        else:
            return il_value

    def expr_ctype(self, symbol_table):
        """Return the undecayed CType of this expression.

        This function produces errors and warnings just as make_code does.
        """
        dummy = ILCode()
        return self.make_code_raw(dummy, symbol_table).ctype

    def lvalue(self, il_code, symbol_table):
        """Return an LValue object corresponding to this, or None."""
        return None

    def make_code_raw(self, il_code, symbol_table):
        """Generate code for the given node.

        Return the undecayed result. That is, do not decay function or
        array types into their pointer equivalents.

        Note that because the expr_ctype function inserts a dummy ILCode
        object, this function should generally not reference any information
        stored in the ILCode object when generating code.
        """
        raise NotImplementedError


class MainNode(Node):
    """General rule for the main function.

    This node will be removed once function definition is supported.

    block_items (List[statement, declaration]) - List of the statements and
    declarations in the main function.

    """

    symbol = Node.MAIN_FUNCTION

    def __init__(self, body):
        """Initialize node."""
        super().__init__()

        # Specifically, we expect 'body' to be a compound statement.
        self.assert_symbol(body, Node.STATEMENT)

        self.body = body

    def make_code(self, il_code, symbol_table):
        """Make IL code for the function body.

        At the end, this function adds code for an artificial return call
        for if the provided function body completes without returning.

        """
        self.body.make_code(il_code, symbol_table)

        return_node = ReturnNode(NumberNode(Token(token_kinds.number, "0")),
                                 None)
        return_node.make_code(il_code, symbol_table)


class CompoundNode(Node):
    """Rule for a compound node.

    A compound node is a statement that consists of several
    statements/declarations enclosed in braces.

    """

    symbol = Node.STATEMENT

    def __init__(self, block_items):
        """Initialize node."""
        super().__init__()

        for item in block_items:
            self.assert_symbols(item, [self.STATEMENT, self.DECLARATION])
        self.block_items = block_items

    def make_code(self, il_code, symbol_table):
        """Make IL code for every block item, in order."""
        symbol_table.new_scope()
        for block_item in self.block_items:
            try:
                block_item.make_code(il_code, symbol_table)
            except CompilerError as e:
                error_collector.add(e)
        symbol_table.end_scope()


class ReturnNode(Node):
    """Rule for the return statement.

    return_value (expression) - Value to return.

    """

    symbol = Node.STATEMENT

    def __init__(self, return_value, return_kw):
        """Initialize node."""
        super().__init__()

        self.assert_symbol(return_value, self.EXPRESSION)

        self.return_value = return_value
        self.return_kw = return_kw

    def make_code(self, il_code, symbol_table):
        """Make IL code for returning this value."""
        il_value = self.return_value.make_code(il_code, symbol_table)

        check_cast(il_value, ctypes.integer, self.return_kw)
        il_code.add(il_commands.Return(
            set_type(il_value, ctypes.integer, il_code)))


class NumberNode(ExpressionNode):
    """Expression that is just a single number.

    number (Token(Number)) - Number this expression represents.

    """

    def __init__(self, number):
        """Initialize node."""
        super().__init__()

        self.assert_kind(number, token_kinds.number)

        self.number = number

    def make_code_raw(self, il_code, symbol_table):
        """Make code for a literal number.

        This function does not actually make any code in the IL, it just
        returns a LiteralILValue that can be used in IL code by the caller.

        """
        v = int(str(self.number))

        if ctypes.int_min <= v <= ctypes.int_max:
            il_value = ILValue(ctypes.integer)
        elif ctypes.long_min <= v <= ctypes.long_max:
            il_value = ILValue(ctypes.longint)
        else:
            descrip = ("integer literal too large to be represented by any " +
                       "integer type")
            raise CompilerError(descrip, self.number.file_name,
                                self.number.line_num)

        il_code.add_literal(il_value, v)

        # Literal integer 0 is a null pointer constant
        if v == 0:
            il_value.null_ptr_const = True

        return il_value


class IdentifierNode(ExpressionNode):
    """Expression that is a single identifier.

    identifier (Token(Identifier)) - Identifier this expression represents.

    """

    def __init__(self, identifier):
        """Initialize node."""
        super().__init__()

        self.assert_kind(identifier, token_kinds.identifier)

        self.identifier = identifier

    def make_code_raw(self, il_code, symbol_table):
        """Make code for an identifier.

        This function performs a lookup in the symbol table, and returns the
        corresponding ILValue.

        """
        return symbol_table.lookup_tok(self.identifier)

    def lvalue(self, il_code, symbol_table):
        """Return the LValue form of this identifier, or None."""
        var = symbol_table.lookup_tok(self.identifier)
        return LValue(LValue.DIRECT, var)


class ExprStatementNode(Node):
    """Statement that contains just an expression."""

    symbol = Node.STATEMENT

    def __init__(self, expr):
        """Initialize node."""
        super().__init__()

        self.assert_symbol(expr, self.EXPRESSION)

        self.expr = expr

    def make_code(self, il_code, symbol_table):
        """Make code for the expression.

        An ILValue is returned, but we ignore it.

        """
        self.expr.make_code(il_code, symbol_table)


class ParenExprNode(ExpressionNode):
    """Expression in parentheses."""

    def __init__(self, expr):
        """Initialize node."""
        super().__init__()

        self.assert_symbol(expr, self.EXPRESSION)

        self.expr = expr

    def make_code_raw(self, il_code, symbol_table):
        """Make code for the expression in the parentheses."""
        return self.expr.make_code(il_code, symbol_table)

    def lvalue(self, il_code, symbol_table):
        """Return the LValue form of this identifier, or None."""
        return self.expr.lvalue(il_code, symbol_table)


class IfStatementNode(Node):
    """If statement.

    conditional - Condition expression of the if statement.
    statement - Statement to be executed by the if statement. Note this is
    very often a compound-statement blocked out with curly braces.

    """

    symbol = Node.STATEMENT

    def __init__(self, conditional, statement):
        """Initialize node."""
        super().__init__()

        self.assert_symbol(conditional, Node.EXPRESSION)
        self.assert_symbol(statement, Node.STATEMENT)

        self.conditional = conditional
        self.statement = statement

    def make_code(self, il_code, symbol_table):
        """Make code for this node."""
        try:
            label = il_code.get_label()
            condition = self.conditional.make_code(il_code, symbol_table)
            il_code.add(il_commands.JumpZero(condition, label))
            self.statement.make_code(il_code, symbol_table)
            il_code.add(il_commands.Label(label))
        except CompilerError as e:
            error_collector.add(e)


class BinaryOperatorNode(ExpressionNode):
    """Expression that is a sum/difference/xor/etc of two expressions.

    left_expr (expression) - Expression on left side.
    operator (Token) - Token representing this operator.
    right_expr (expression) - Expression on right side.

    """

    def __init__(self, left_expr, operator, right_expr):
        """Initialize node."""
        super().__init__()

        self.assert_symbol(left_expr, self.EXPRESSION)
        self.assert_symbol(right_expr, self.EXPRESSION)

        self.left_expr = left_expr
        self.operator = operator
        self.right_expr = right_expr

    def make_code_raw(self, il_code, symbol_table):
        """Make code for this node."""

        # If = operator
        if self.operator == Token(token_kinds.equals):
            return self._make_equals_code(il_code, symbol_table)

        # Make code for both operands
        left = self.left_expr.make_code(il_code, symbol_table)
        right = self.right_expr.make_code(il_code, symbol_table)

        # If arithmetic type
        if (left.ctype.type_type == CType.ARITH and
              right.ctype.type_type == CType.ARITH):
            return self._make_integer_code(right, left, il_code)

        # If operator is == or !=
        elif (self.operator.kind == token_kinds.twoequals or
              self.operator.kind == token_kinds.notequal):
            return self._make_nonarith_equality_code(left, right, il_code)

        # If operator is addition
        elif self.operator.kind == token_kinds.plus:
            return self._make_nonarith_plus_code(left, right, il_code)

        # If operator is multiplication or division
        elif self.operator.kind in {token_kinds.star, token_kinds.slash}:
            if self.operator.kind == token_kinds.star:
                descrip = "invalid operand types for binary multiplication"
            else:  # self.operator.kind == token_kinds.slash
                descrip = "invalid operand types for binary division"

            raise CompilerError(descrip, self.operator.file_name,
                                self.operator.line_num)

        else:
            raise NotImplementedError("Unsupported operands")

    def _promo_type(self, type1, type2):
        """Return the type these both should be promoted to for computation."""

        # If an int can represent all values of the original type, the value is
        # converted to an int; otherwise, it is converted to an unsigned
        # int. These are called the integer promotions.

        # All types of size < 4 can fit in int, so we promote directly to int
        type1_promo = ctypes.integer if type1.size < 4 else type1
        type2_promo = ctypes.integer if type2.size < 4 else type2

        # If both operands have the same type, then no further conversion is
        # needed.
        if type1_promo == type2_promo:
            return type1_promo

        # Otherwise, if both operands have signed integer types or both have
        # unsigned integer types, the operand with the type of lesser integer
        # conversion rank is converted to the type of the operand with greater
        # rank.
        elif type1_promo.signed == type2_promo.signed:
            return max([type1_promo, type2_promo], key=lambda t: t.size)

        # Otherwise, if the operand that has unsigned integer type has rank
        # greater or equal to the rank of the type of the other operand, then
        # the operand with signed integer type is converted to the type of the
        # operand with unsigned integer type.
        elif not type1_promo.signed and type1_promo.size >= type2_promo.size:
            return type1_promo
        elif not type2_promo.signed and type2_promo.size >= type1_promo.size:
            return type2_promo

        # Otherwise, if the type of the operand with signed integer type can
        # represent all of the values of the type of the operand with unsigned
        # integer type, then the operand with unsigned integer type is
        # converted to the type of the operand with signed integer type.
        elif type1_promo.signed and type1_promo.size > type2_promo.size:
            return type1_promo
        elif type2_promo.signed and type2_promo.size > type1_promo.size:
            return type2_promo

        # Otherwise, both operands are converted to the unsigned integer type
        # corresponding to the type of the operand with signed integer type.
        elif type1_promo.signed:
            return ctypes.to_unsigned(type1_promo)
        elif type2_promo.signed:
            return ctypes.to_unsigned(type2_promo)

    def _make_integer_code(self, right, left, il_code):
        """Make code with given arithmetic operands.

        right - Expression on right side of operator
        left - Expression on left side of operator
        il_code - ILCode object to add code to

        """
        # Cast both operands to a common type if necessary.
        new_type = self._promo_type(left.ctype, right.ctype)
        left_cast = set_type(left, new_type, il_code)
        right_cast = set_type(right, new_type, il_code)

        # Mapping from a token_kind to the ILCommand it corresponds to.
        cmd_map = {token_kinds.plus: il_commands.Add,
                   token_kinds.star: il_commands.Mult,
                   token_kinds.slash: il_commands.Div,
                   token_kinds.twoequals: il_commands.EqualCmp,
                   token_kinds.notequal: il_commands.NotEqualCmp}

        # Commands that output an ILValue of integer type rather than of the
        # input type.
        cmp_cmds = {il_commands.EqualCmp, il_commands.NotEqualCmp}
        if cmd_map[self.operator.kind] in cmp_cmds:
            output = ILValue(ctypes.integer)
        else:
            output = ILValue(new_type)
        il_code.add(cmd_map[self.operator.kind](output, left_cast, right_cast))
        return output

    def _make_equals_code(self, il_code, symbol_table):
        """Make code if this is a = node."""
        right = self.right_expr.make_code(il_code, symbol_table)
        lvalue = self.left_expr.lvalue(il_code, symbol_table)

        if lvalue and lvalue.modable():
            return lvalue.set_to(right, il_code, self.operator)
        else:
            descrip = "expression on left of '=' is not assignable"
            raise CompilerError(descrip, self.operator.file_name,
                                self.operator.line_num)

    def _make_nonarith_plus_code(self, left, right, il_code):
        """Make code for + operator for non-arithmetic operands."""

        # One operand should be pointer to complete object type, and the
        # other should be any integer type.
        # TODO: Check if IntegerCType, not just CType.ARITH (floats, etc.)
        if (left.ctype.type_type == CType.POINTER and
                    right.ctype.type_type == CType.ARITH):
            arith_op, pointer_op = right, left
        elif (right.ctype.type_type == CType.POINTER and
                      left.ctype.type_type == CType.ARITH):
            arith_op, pointer_op = left, right
        else:
            descrip = "invalid operand types for binary addition"
            raise CompilerError(descrip, self.operator.file_name,
                                self.operator.line_num)

        # Cast the integer operand to a long for multiplication.
        l_arith_op = set_type(arith_op, ctypes.unsig_longint, il_code)

        # Amount to shift the pointer by
        shift = ILValue(ctypes.unsig_longint)

        # ILValue for the output pointer
        out = ILValue(pointer_op.ctype)

        # Size of pointed-to object as a literal IL value
        size = ILValue(ctypes.unsig_longint)
        il_code.add_literal(size, str(pointer_op.ctype.arg.size))

        il_code.add(il_commands.Mult(shift, l_arith_op, size))
        il_code.add(il_commands.Add(out, pointer_op, shift))
        return out

    def _make_nonarith_equality_code(self, left, right, il_code):
        """Make code for == and != operators for non-arithmetic operands."""

        # If either operand is a null pointer constant, cast it to the
        # other's pointer type.
        if (left.ctype.type_type == CType.POINTER and
                right.null_ptr_const):
            right = set_type(right, left.ctype, il_code)
        elif (right.ctype.type_type == CType.POINTER and
                  left.null_ptr_const):
            left = set_type(left, right.ctype, il_code)

        # If both operands are not pointer types, warn!
        if (left.ctype.type_type != CType.POINTER or
             right.ctype.type_type != CType.POINTER):
            descrip = "comparison between incomparable types"
            error_collector.add(
                CompilerError(descrip, self.operator.file_name,
                              self.operator.line_num, True))

        # If one side is pointer to void, cast the other to same.
        elif left.ctype.arg == ctypes.void:
            right = set_type(right, left.ctype, il_code)
        elif right.ctype.arg == ctypes.void:
            left = set_type(left, right.ctype, il_code)

        # If both types are still incompatible, warn!
        elif not left.ctype.compatible(right.ctype):
            descrip = "comparison between distinct pointer types"
            error_collector.add(
                CompilerError(descrip, self.operator.file_name,
                              self.operator.line_num, True))

        # Now, we can do comparison
        output = ILValue(ctypes.integer)
        if self.operator.kind == token_kinds.twoequals:
            cmd = il_commands.EqualCmp
        else:
            cmd = il_commands.NotEqualCmp
        il_code.add(cmd(output, left, right))
        return output


class AddrOfNode(ExpressionNode):
    """Expression produced by getting the address of a variable.

    expr (expression) - lvalue for which to get the address
    op (Token) - Token representing this operator. Used for error reporting.

    """

    def __init__(self, expr, op):
        """Initialize node."""
        super().__init__()

        self.assert_symbol(expr, Node.EXPRESSION)
        self.expr = expr
        self.op = op

    def make_code_raw(self, il_code, symbol_table):
        """Make code for getting the address."""
        if not isinstance(self.expr, IdentifierNode):
            descrip = "lvalue required as unary '&' operand"
            raise CompilerError(descrip, self.op.file_name, self.op.line_num)

        lvalue = self.expr.make_code_raw(il_code, symbol_table)
        out = ILValue(PointerCType(lvalue.ctype))
        il_code.add(il_commands.AddrOf(out, lvalue))

        return out


class DerefNode(ExpressionNode):
    """Expression produced by dereferencing a pointer.

    expr (expression) - pointer to dereference

    """

    def __init__(self, expr, op):
        """Initialize node."""
        super().__init__()

        self.assert_symbol(expr, Node.EXPRESSION)
        self.expr = expr
        self.op = op

        # Cache the expression IL value, so calls to make_code_raw or lvalue
        # only calculate the expression once. This is important in
        # expressions like
        #
        #     *func() += 1;
        #
        # where evaluating the expression multiple times can produce
        # additional side effects.
        self._cache_lvalue = None

    def make_code_raw(self, il_code, symbol_table):
        """Make code for getting the value at the address."""
        lvalue = self.lvalue(il_code, symbol_table)

        out = ILValue(lvalue.il_value.ctype.arg)
        il_code.add(il_commands.ReadAt(out, lvalue.il_value))
        return out

    def lvalue(self, il_code, symbol_table):
        """Return the LValue form of this identifier, or None."""
        if not self._cache_lvalue:
            addr = self.expr.make_code(il_code, symbol_table)

            if addr.ctype.type_type != CType.POINTER:
                descrip = "operand of unary '*' must have pointer type"
                raise CompilerError(descrip, self.op.file_name,
                                    self.op.line_num)

            self._cache_lvalue = LValue(LValue.INDIRECT, addr)

        return self._cache_lvalue


class FunctionCallNode(ExpressionNode):
    """Expression produced by calling a function.

    For example:     f(3, 4, 5)     (&f)()

    Currently does not support function pointers.

    func (expression) - Expression node describing the function to call. Often
    just an identifier.

    args (List(expression)) - List of expression nodes of each argument to the
    function, from left to right order.

    """

    def __init__(self, func, args):
        """Initialize node."""
        super().__init__()

        self.assert_symbol(func, Node.EXPRESSION)
        for arg in args:
            self.assert_symbol(arg, Node.EXPRESSION)

        self.func = func
        self.args = args

    def make_code_raw(self, il_code, symbol_table):
        """Make code for this function call."""
        if isinstance(self.func, IdentifierNode):
            try:
                il_func = self.func.make_code(il_code, symbol_table)
            except CompilerError:
                # If function not found, generate a default one and mark as
                # extern.
                il_func = ILValue(FunctionCType(None, ctypes.integer))
                il_code.add_variable(il_func, self.func.identifier.content)
                il_code.add_extern(self.func.identifier.content)

                # Log a warning
                descrip = "implicit declaration of function '{}'"
                error_collector.add(
                    CompilerError(descrip.format(self.func.identifier.content),
                                  self.func.identifier.file_name,
                                  self.func.identifier.line_num,
                                  warning=True))

            if il_func.ctype.type_type != CType.FUNCTION:
                descrip = "called object is not a function '{}'"
                raise CompilerError(
                    descrip.format(self.func.identifier.content),
                    self.func.identifier.file_name,
                    self.func.identifier.line_num)

            # If the function has a specified argument list, verify it matches
            # with given arguments and cast if necessary.
            if il_func.ctype.args:
                raise NotImplementedError("functions with arguments")
            else:
                # Function has unspecified argument list, so cast everything to
                # integer.
                def c(arg):
                    a = arg.make_code(il_code, symbol_table)
                    check_cast(a, ctypes.integer, None)
                    return set_type(a, ctypes.integer, il_code)
                cast_args = list(map(c, self.args))

            output = ILValue(il_func.ctype.ret)
            il_code.add(il_commands.Call(il_func, cast_args, output))

            return output
        else:
            raise NotImplementedError("fancy function call")


class DeclarationNode(Node):
    """Line of a general variable declaration(s).

    For example:  int a = 3, *b, c[] = {3, 2, 5};

    Currently, only supports declaration of a single integer or char variable
    with no initializer.

    variable_name (Token(identifier)) - The identifier representing the new
    variable name.
    ctype (CType) - The ctype of this variable

    """

    symbol = Node.DECLARATION

    def __init__(self, variable_name, ctype):
        """Initialize node."""
        super().__init__()

        self.assert_kind(variable_name, token_kinds.identifier)

        self.variable_name = variable_name
        self.ctype = ctype

    def make_code(self, il_code, symbol_table):
        """Make code for this declaration.

        This function does not generate any IL code; it just adds the declared
        variable to the symbol table.

        """
        if self.ctype == ctypes.void:
            raise CompilerError("variable of void type declared",
                                self.variable_name.file_name,
                                self.variable_name.line_num)

        symbol_table.add(self.variable_name, self.ctype, il_code)
