"""Tree package - AST node classes.

This package provides all AST node classes organized by functionality.
All public classes (not starting with underscore) are exposed at the
package level.
"""

# Base classes
from shivyc.tree.base_nodes import Node

# Control flow statements
from shivyc.tree.control_flow_nodes import (
    Return, Break, Continue, IfStatement, WhileStatement, ForStatement
)

# General statement and declaration nodes
from shivyc.tree.general_nodes import (
    Root, Compound, EmptyStatement, ExprStatement, Declaration, DeclInfo
)

# Primary expressions
from shivyc.tree.primary_exprs import (
    MultiExpr, Number, String, Identifier, ParenExpr
)

# Arithmetic operations
from shivyc.tree.arithmetic_exprs import (
    Plus, Minus, Mult, Div, Mod, RBitShift, LBitShift
)

# Comparison operations
from shivyc.tree.comparison_exprs import (
    Equality, Inequality, LessThan, GreaterThan, LessThanOrEq,
    GreaterThanOrEq
)

# Boolean operations
from shivyc.tree.boolean_exprs import (
    BoolAnd, BoolOr, BoolNot
)

# Assignment operations
from shivyc.tree.assignment_exprs import (
    Equals, PlusEquals, MinusEquals, StarEquals, DivEquals, ModEquals
)

# Unary operations
from shivyc.tree.unary_exprs import (
    PreIncr, PostIncr, PreDecr, PostDecr, UnaryPlus, UnaryMinus, Compl
)

# Memory operations and member access
from shivyc.tree.memory_exprs import (
    AddrOf, Deref, ArraySubsc, ObjMember, ObjPtrMember
)

# Type operations
from shivyc.tree.type_exprs import (
    SizeofExpr, SizeofType, Cast
)

# Function calls
from shivyc.tree.call_exprs import (
    FuncCall
)

# Expose all public classes in __all__
__all__ = [
    # Base classes
    'Node',

    # Control flow statements
    'Return', 'Break', 'Continue',
    'IfStatement', 'WhileStatement', 'ForStatement',

    # General statement and declaration nodes
    'Root', 'Compound', 'EmptyStatement', 'ExprStatement', 'Declaration',
    'DeclInfo',

    # Primary expressions
    'MultiExpr', 'Number', 'String', 'Identifier', 'ParenExpr',

    # Arithmetic operations
    'Plus', 'Minus', 'Mult', 'Div', 'Mod', 'RBitShift', 'LBitShift',

    # Comparison operations
    'Equality', 'Inequality', 'LessThan', 'GreaterThan', 'LessThanOrEq',
    'GreaterThanOrEq',

    # Boolean operations
    'BoolAnd', 'BoolOr', 'BoolNot',

    # Assignment operations
    'Equals', 'PlusEquals', 'MinusEquals', 'StarEquals', 'DivEquals',
    'ModEquals',

    # Unary operations
    'PreIncr', 'PostIncr', 'PreDecr', 'PostDecr', 'UnaryPlus',
    'UnaryMinus', 'Compl',

    # Memory operations and member access
    'AddrOf', 'Deref', 'ArraySubsc', 'ObjMember', 'ObjPtrMember',

    # Type operations
    'SizeofExpr', 'SizeofType', 'Cast',

    # Function calls
    'FuncCall'
]
