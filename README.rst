ShivyC
======

| |Build Status| |Code Coverage|


ShivyC is a dependency-free C compiler written in Python 3, targeting Linux
x86-64 machines. ShivyC seeks to eventually support the entire C11
standard and produce reasonably efficient code. For ShivyC’s current
feature set, see the test files in the `tests/general\_tests`_ and
`tests/feature\_tests`_ directories.

ShivyC is a rewrite from scratch of my older attempt at a C compiler,
`ShivC`_, with much more emphasis on feature completeness and code
quality. See the ShivC README for more details on the target
improvements.

Quickstart
------------

For compilation of C code, ShivyC only requires Python 3. Assembling and linking are done using the GNU binutils and glibc, which you almost certainly already have installed.

To install ShivyC:
::

    pip3 install shivyc

For command line usage info:
::

    shivyc

To create, compile, and run an example program:
::

    printf "%s\n" '#include <stdio.h>' > test.c
    printf "%s\n" 'int main() { printf("hello, world!\n"); }' >> test.c
    shivyc test.c
    ./out

To run the tests:
::
    git clone https://github.com/ShivamSarodia/ShivyC.git
    cd ShivyC
    python3 -m unittest discover



Implementation Overview
-----------------------

Preprocessor
^^^^^^^^^^^^

ShivyC currently has a very limited preprocessor that parses out
comments and expands #include directives. These features are implemented
between ``lexer.py`` and ``preproc.py``. A more complete preprocessor
will be implemented.

Lexer
^^^^^

The ShivyC lexer is implemented primarily in ``lexer.py``. Additionally,
``tokens.py`` contains definitions of the token classes used in the
lexer and ``token_kinds.py`` contains instances of recognized keyword
and symbol tokens.

Parser
^^^^^^

The ShivyC parser uses recursive descent techniques for all parsing. It
is implented in ``parser/*.py`` and creates a parse tree of nodes
defined in ``tree/nodes.py`` and ``tree/expr_nodes.py``.

IL generation
^^^^^^^^^^^^^

ShivyC traverses the parse tree to generate a flat custom IL
(intermediate language). The commands for this IL are in
``il_cmds/*.py``. Objects used for IL generation are in ``il_gen.py``,
but most of the IL generating code is in the ``make_code`` function of
each tree node in ``tree/*.py``.

ASM generation
^^^^^^^^^^^^^^

ShivyC sequentially reads the IL commands, converting each into x86-64
assembly code. ShivyC performs register allocation using George and
Appel’s iterated register coalescing algorithm; see References below.
The general ASM generation functionality is in ``asm_gen.py``, but much
of the ASM generating code is in the ``make_asm`` function of each IL
command in ``il_cmds/*.py``.

Contributing
------------

ShivyC has so far been an entirely individual project. That said, pull
requests are welcome if they pass flake8 and are well-tested.

References
----------

-  C11 Specification -
   http://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf
-  x86\_64 ABI -
   http://web.archive.org/web/20160801075139/http://www.x86-64.org/documentation/abi.pdf
-  Iterated Register Coalescing (George and Appel) -
   https://www.cs.purdue.edu/homes/hosking/502/george.pdf

.. _tests/general\_tests: https://github.com/ShivamSarodia/ShivyC/tree/master/tests/general_tests
.. _tests/feature\_tests: https://github.com/ShivamSarodia/ShivyC/tree/master/tests/feature_tests
.. _ShivC: https://github.com/ShivamSarodia/ShivC

.. |Build Status| image:: https://travis-ci.org/ShivamSarodia/ShivyC.svg?branch=master
   :target: https://travis-ci.org/ShivamSarodia/ShivyC
.. |Code Coverage| image:: https://codecov.io/gh/ShivamSarodia/ShivyC/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/ShivamSarodia/ShivyC
