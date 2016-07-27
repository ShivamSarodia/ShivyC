"""Defines a list of token kinds currently recognized

"""

from tokens import TokenKind

keyword_kinds = []
symbol_kinds = []

# Until function definition is ready, we define `main` as a hardcoded keyword
main = TokenKind("main", keyword_kinds)

int_kw = TokenKind("int", keyword_kinds)
return_kw = TokenKind("return", keyword_kinds)

plus = TokenKind("+", symbol_kinds)
star = TokenKind("*", symbol_kinds)

open_paren = TokenKind("(", symbol_kinds)
close_paren = TokenKind(")", symbol_kinds)
open_brack = TokenKind("{", symbol_kinds)
close_brack = TokenKind("}", symbol_kinds)

semicolon = TokenKind(";", symbol_kinds)

identifier = TokenKind()
number = TokenKind()
