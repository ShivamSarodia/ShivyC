"""Defines a list of token kinds currently recognized

"""

from token import TokenKind

int_kw = TokenKind("int")  # `kw` is short for 'keyword'
main = TokenKind("main")
open_paren = TokenKind("(")
close_paren = TokenKind(")")
open_brack = TokenKind("{")
return_kw = TokenKind("return")
number = TokenKind()
close_brack = TokenKind("}")
