"""Classes for the nodes that form our abstract syntax tree (AST).

Each node corresponds to a rule in the C grammar and has a make_code function
that generates code in our three-address IL.

"""

import ctypes
import token_kinds
import il_commands
from errors import CompilerError, error_collector
from il_gen import TempILValue
from il_gen import LiteralILValue
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
        return False

    def assert_symbol(self, node, symbol_name):
        """Check whether the provided node is of the given symbol.

        Useful for enforcing tree structure. Raises an exception if the node
        represents a rule that does not produce the expected symbol.

        """
        if node.symbol != symbol_name:
            raise ValueError("malformed tree: expected symbol '" + str(
                symbol_name) + "' but got '" + str(node.symbol) + "'")

    def assert_symbols(self, node, symbol_names):
        """Check whether the provided node is one of the given symbols.

        Useful for enforcing tree structure. Raises an exception if the node
        represents a rule that produces none of the symbols in symbol_names.

        """
        if node.symbol not in symbol_names:
            raise ValueError("malformed tree: unexpected symbol '" + str(
                node.symbol) + "'")

    def assert_kind(self, token, kind):
        """Check whether the provided token is of the given token kind.

        Useful for enforcing tree structure. Raises an exception if the token
        does not have the given kind.

        """
        if token.kind != kind:
            raise ValueError("malformed tree: expected token_kind '" + str(
                kind) + "' but got '" + str(token.kind) + "'")

    def cast(self, il_value, ctype, il_code):
        """If necessary, emit code to cast given il_value to the given ctype.

        Returns an IL value of given ctype, or raises a CompilerError if type
        conversion cannot be done.

        """
        if il_value.ctype == ctype:
            # Already correct type, no need to cast
            return il_value
        else:
            # TODO: Raise error/warning on sketchy casts
            new = TempILValue(ctype)
            il_code.add(il_commands.Set(new, il_value))
            return new


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

        return_node = ReturnNode(NumberNode(Token(token_kinds.number, "0")))
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
        for block_item in self.block_items:
            try:
                block_item.make_code(il_code, symbol_table)
            except CompilerError as e:
                error_collector.add(e)


class ReturnNode(Node):
    """Rule for the return statement.

    return_value (expression) - Value to return.

    """

    symbol = Node.STATEMENT

    def __init__(self, return_value):
        """Initialize node."""
        super().__init__()

        self.assert_symbol(return_value, self.EXPRESSION)

        self.return_value = return_value

    def make_code(self, il_code, symbol_table):
        """Make IL code for returning this value."""
        il_value = self.return_value.make_code(il_code, symbol_table)
        il_code.add(il_commands.Return(
            self.cast(il_value, ctypes.integer, il_code)))


class NumberNode(Node):
    """Expression that is just a single number.

    number (Token(Number)) - Number this expression represents.

    """

    symbol = Node.EXPRESSION

    def __init__(self, number):
        """Initialize node."""
        super().__init__()

        self.assert_kind(number, token_kinds.number)

        self.number = number

    def make_code(self, il_code, symbol_table):
        """Make code for a literal number.

        This function does not actually make any code in the IL, it just
        returns a LiteralILValue that can be used in IL code by the caller.

        """
        # TODO: Support a long integer, etc. We can be a smarter about the type
        # we assign a number here, based on the size of the number etc.
        return LiteralILValue(ctypes.integer, str(self.number))


class IdentifierNode(Node):
    """Expression that is a single identifier.

    identifier (Token(Identifier)) - Identifier this expression represents.

    """

    symbol = Node.EXPRESSION

    def __init__(self, identifier):
        """Initialize node."""
        super().__init__()

        self.assert_kind(identifier, token_kinds.identifier)

        self.identifier = identifier

    def make_code(self, il_code, symbol_table):
        """Make code for an identifier.

        This function performs a lookup in the symbol table, and returns the
        corresponding ILValue.

        """
        return symbol_table.lookup_tok(self.identifier)


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


class ParenExprNode(Node):
    """Expression in parentheses."""

    symbol = Node.EXPRESSION

    def __init__(self, expr):
        """Initialize node."""
        super().__init__()

        self.assert_symbol(expr, self.EXPRESSION)

        self.expr = expr

    def make_code(self, il_code, symbol_table):
        """Make code for the expression in the parentheses."""
        return self.expr.make_code(il_code, symbol_table)


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


class BinaryOperatorNode(Node):
    """Expression that is a sum/difference/xor/etc of two expressions.

    left_expr (expression) - Expression on left side.
    operator (Token) - Token representing this operator.
    right_expr (expression) - Expression on right side.

    """

    symbol = Node.EXPRESSION

    def __init__(self, left_expr, operator, right_expr):
        """Initialize node."""
        super().__init__()

        self.assert_symbol(left_expr, self.EXPRESSION)
        self.assert_symbol(right_expr, self.EXPRESSION)

        self.left_expr = left_expr
        self.operator = operator
        self.right_expr = right_expr

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

    def make_code(self, il_code, symbol_table):
        """Make code for this node."""
        # If equals, call make_equals_code immediately.
        if self.operator == Token(token_kinds.equals):
            return self.make_equals_code(il_code, symbol_table)

        # Make code for both operands and cast if necessary.
        left = self.left_expr.make_code(il_code, symbol_table)
        right = self.right_expr.make_code(il_code, symbol_table)

        new_type = self._promo_type(left.ctype, right.ctype)
        left_cast = self.cast(left, new_type, il_code)
        right_cast = self.cast(right, new_type, il_code)
        output = TempILValue(new_type)

        cmd_map = {token_kinds.plus: il_commands.Add,
                   token_kinds.star: il_commands.Mult,
                   token_kinds.slash: il_commands.Div}

        il_code.add(cmd_map[self.operator.kind](output, left_cast, right_cast))
        return output

    def make_equals_code(self, il_code, symbol_table):
        """Make code if this is a = node."""
        if isinstance(self.left_expr, IdentifierNode):
            right = self.right_expr.make_code(il_code, symbol_table)
            left = symbol_table.lookup_tok(self.left_expr.identifier)
            right_cast = self.cast(right, left.ctype, il_code)

            il_code.add(il_commands.Set(left, right_cast))
            return left
        else:
            descrip = "expression on left of '=' is not assignable"
            raise CompilerError(descrip, self.operator.file_name,
                                self.operator.line_num)


class DeclarationNode(Node):
    """Line of a general variable declaration(s).

    For example:  int a = 3, *b, c[] = {3, 2, 5};

    Currently, only supports declaration of a single integer or char variable
    with no initializer.

    variable_name (Token(identifier)) - The identifier representing the new
    variable name.
    ctype_token(Token(int_kw or char_kw)) - The type of this variable.
    signed (bool) - Whether this variable is signed or unsigned.

    """

    symbol = Node.DECLARATION

    def __init__(self, variable_name, ctype_token, signed):
        """Initialize node."""
        super().__init__()

        self.assert_kind(variable_name, token_kinds.identifier)

        self.variable_name = variable_name
        self.ctype_token = ctype_token
        self.signed = signed

    def make_code(self, il_code, symbol_table):
        """Make code for this declaration.

        This function does not generate any IL code; it just adds the declared
        variable to the symbol table.

        """
        type_map = {(token_kinds.char_kw, True): ctypes.char,
                    (token_kinds.char_kw, False): ctypes.unsig_char,
                    (token_kinds.short_kw, True): ctypes.short,
                    (token_kinds.short_kw, False): ctypes.unsig_short,
                    (token_kinds.int_kw, True): ctypes.integer,
                    (token_kinds.int_kw, False): ctypes.unsig_int,
                    (token_kinds.long_kw, True): ctypes.longint,
                    (token_kinds.long_kw, False): ctypes.unsig_longint}

        ctype = type_map[(self.ctype_token.kind, self.signed)]
        symbol_table.add(self.variable_name.content, ctype)
