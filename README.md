# ShivyC [![Build Status](https://travis-ci.org/ShivamSarodia/ShivyC.svg?branch=master)](https://travis-ci.org/ShivamSarodia/ShivyC) [![Code Coverage](https://codecov.io/gh/ShivamSarodia/ShivyC/branch/master/graph/badge.svg)](https://codecov.io/gh/ShivamSarodia/ShivyC)

### A hobby C compiler created in Python.

![ShivyC demo GIF.](https://raw.githubusercontent.com/ShivamSarodia/ShivyC/master/demo.gif)

---

ShivyC is a hobby C compiler written in Python 3 that supports a subset of the C11 standard and generates reasonably efficient binaries, including some optimizations. ShivyC also generates helpful compile-time error messages.

This [implementation of a trie](tests/general_tests/trie/trie.c) is an example of what ShivyC can compile today. For a more comprehensive list of features, see the [feature test directory](tests/feature_tests).

## Quickstart

### x86-64 Linux
ShivyC requires only Python 3.6 or later to compile C code. Assembling and linking are done using the GNU binutils and glibc, which you almost certainly already have installed.

To install ShivyC:
```
pip3 install shivyc
```
To create, compile, and run an example program:
```c
$ vim hello.c
$ cat hello.c

#include <stdio.h>
int main() {
  printf("hello, world!\n");
}

$ shivyc hello.c
$ ./out
hello, world!
```
To run the tests:
```
git clone https://github.com/ShivamSarodia/ShivyC.git
cd ShivyC
python3 -m unittest discover
```

### Other Architectures
For the convenience of those not running Linux, the [`docker/`](docker/) directory provides a Dockerfile that sets up an x86-64 Linux Ubuntu environment with everything necessary for ShivyC. To use this, run:
```
git clone https://github.com/ShivamSarodia/ShivyC.git
cd ShivyC
docker build -t shivyc docker/
docker/shell
```
This will open up a shell in an environment with ShivyC installed and ready to use with
```
shivyc any_c_file.c           # to compile a file
python3 -m unittest discover  # to run tests
```
The Docker ShivyC executable will update live with any changes made in your local ShivyC directory.

## Implementation Overview
#### Preprocessor
ShivyC today has a very limited preprocessor that parses out comments and expands `#include` directives. These features are implemented between [`lexer.py`](shivyc/lexer.py) and [`preproc.py`](shivyc/lexer.py).

#### Lexer
The ShivyC lexer is implemented primarily in [`lexer.py`](shivyc/lexer.py). Additionally, [`tokens.py`](shivyc/tokens.py) contains definitions of the token classes used in the lexer and [`token_kinds.py`](shivyc/token_kinds.py) contains instances of recognized keyword and symbol tokens.

#### Parser
The ShivyC parser uses recursive descent techniques for all parsing. It is implented in [`parser/*.py`](shivyc/parser/) and creates a parse tree of nodes defined in [`tree/nodes.py`](shivyc/tree/nodes.py) and [`tree/expr_nodes.py`](shivyc/tree/expr_nodes.py).

#### IL generation
ShivyC traverses the parse tree to generate a flat custom IL (intermediate language). The commands for this IL are in [`il_cmds/*.py`](shivyc/il_cmds/) . Objects used for IL generation are in [`il_gen.py`](shivyc/il_gen.py) , but most of the IL generating code is in the `make_code` function of each tree node in [`tree/*.py`](shivyc/tree/).

#### ASM generation
ShivyC sequentially reads the IL commands, converting each into Intel-format x86-64 assembly code. ShivyC performs register allocation using George and Appel’s iterated register coalescing algorithm (see References below). The general ASM generation functionality is in [`asm_gen.py`](shivyc/asm_gen.py) , but much of the ASM generating code is in the `make_asm` function of each IL command in [`il_cmds/*.py`](shivyc/il_cmds/).

## Contributing
Pull requests to ShivyC are very welcome. A good place to start is the [Issues page](https://github.com/ShivamSarodia/ShivyC/issues). All [issues labeled "feature"](https://github.com/ShivamSarodia/ShivyC/issues?q=is%3Aopen+is%3Aissue+label%3Afeature) are TODO tasks. [Issues labeled "bug"](https://github.com/ShivamSarodia/ShivyC/issues?q=is%3Aopen+is%3Aissue+label%3Abug) are individual miscompilations in ShivyC. If you have any questions, please feel free to ask in the comments of the relevant issue or create a new issue labeled "question". Of course, please add test(s) for all new functionality.

Many thanks to our current and past contributers:
* [ShivamSarodia](https://github.com/ShivamSarodia)
* [cclauss](https://github.com/cclauss)
* [TBladen](https://github.com/tbladen)
* [christian-stephen](https://github.com/christian-stephen)
* [jubnzv](https://github.com/jubnzv)
* [eriols](https://github.com/eriols)

## References
- [ShivC](https://github.com/ShivamSarodia/ShivC) - ShivyC is a rewrite from scratch of my old C compiler, ShivC, with much more emphasis on feature completeness and code quality. See the ShivC README for more details.
- C11 Specification - http://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf
- x86_64 ABI - https://github.com/hjl-tools/x86-psABI/wiki/x86-64-psABI-1.0.pdf
- Iterated Register Coalescing (George and Appel) - https://www.cs.purdue.edu/homes/hosking/502/george.pdf
