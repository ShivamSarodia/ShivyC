# ShivyC

[![Build Status](https://travis-ci.org/ShivamSarodia/ShivyC.svg?branch=master)](https://travis-ci.org/ShivamSarodia/ShivyC)
[![Code Coverage](https://codecov.io/gh/ShivamSarodia/ShivyC/branch/master/graph/badge.svg)](https://codecov.io/gh/ShivamSarodia/ShivyC)

ShivyC is a small C compiler written in Python 3, targeting Linux x86-64 machines. Seeks to eventually support the entire C11 standard and produce reasonably efficient code, although it's currently far from meeting these long-term goals. For ShivyC's current feature set, see the test files in the [tests/ctests/](tests/ctests/) directory.

ShivyC is a rewrite from scratch of my older attempt at a C compiler, [ShivC](https://github.com/ShivamSarodia/ShivC), with much more emphasis on feature completeness and code quality. See the ShivC README for more details on the target improvements.

## Running
Requires Python 3 and NASM; tested on NASM 2.11.08. Run `./shivyc.py` for usage info. To run the tests:
```
python3 -m unittest discover
```

## Implementation Overview
#### Preprocessor
ShivyC currently has no preprocessor, besides very primitively parsing out line comments. A decent preprocessor will be implemented.

#### Lexer
The ShivyC lexer is implemented primarily in `lexer.py`. Additionally, `tokens.py` contains definitions of the token classes used in the lexer and `token_kinds.py` contains instances of recognized keyword and symbol tokens.

#### Parser
The ShivyC parser uses recursive descent techniques for most parsing, but a shift-reduce parser for expressions. It is implented in `parser.py` and creates a parse tree of nodes defined in `tree.py`.

#### IL generation
ShivyC traverses the parse tree to generate a flat custom IL (intermediate language). The commands for this IL are in `il_commands.py`. The general IL generation functionality is in `il_gen.py`, but most of the IL generating code is in the `make_code` function of each tree node in `tree.py`.

#### ASM generation
ShivyC sequentially reads the IL commands, converting each into x86-64 assembly code. ShivyC performs register allocation using George and Appel's iterated register coalescing algorithm; see References below. The general ASM generation functionality is in `asm_gen.py`, but much of the ASM generating code is in the `make_asm` function of each IL command in `il_commands.py`.

## Contributing
ShivyC has so far been an entirely individual project. That said, pull requests are welcome if they pass flake8 and are well-tested.

## References
- C11 Specification - http://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf
- x86_64 ABI - http://web.archive.org/web/20160801075139/http://www.x86-64.org/documentation/abi.pdf
- Iterated Register Coalescing (George and Appel) - https://www.cs.purdue.edu/homes/hosking/502/george.pdf
