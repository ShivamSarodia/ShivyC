#!/usr/bin/env python3
"""Main executable for ShivyC compiler.

For usage, run "./shivyc.py --help".

"""

import argparse
import pathlib
import subprocess
import sys

import lexer
import preproc

from errors import error_collector, CompilerError
from parser.parser import parse
from il_gen import ILCode
from il_gen import SymbolTable
from asm_gen import ASMCode
from asm_gen import ASMGen


def main():
    """Run the main compiler script."""
    # Each of these functions should add any issues to the global
    # error_collector -- NOT raise them. After each stage of the compiler,
    # compiliation only proceeds if no errors were found.

    arguments = get_arguments()

    code, filename = read_file(arguments)
    if not error_collector.ok():
        error_collector.show()
        return 1

    token_list = lexer.tokenize(code, filename)
    if not error_collector.ok():
        error_collector.show()
        return 1

    token_list = preproc.process(token_list, filename)
    if not error_collector.ok():
        error_collector.show()
        return 1

    ast_root = parse(token_list)
    if not error_collector.ok():
        error_collector.show()
        return 1

    il_code = ILCode()
    ast_root.make_code(il_code, SymbolTable())
    if not error_collector.ok():
        error_collector.show()
        return 1

    # Display the IL generated if indicated on the command line.
    if arguments.show_il:
        print(str(il_code))

    asm_code = ASMCode()
    ASMGen(il_code, asm_code, arguments).make_asm()
    asm_source = asm_code.full_code()
    if not error_collector.ok():
        error_collector.show()
        return 1

    asm_filename = "out.s"
    write_asm(asm_source, asm_filename)
    if not error_collector.ok():
        error_collector.show()
        return 1

    assemble_and_link("out", asm_filename, "out.o")
    if not error_collector.ok():
        error_collector.show()
        return 1

    error_collector.show()
    return 0


def get_arguments():
    """Get the command-line arguments.

    This function sets up the argument parser and returns an object storing the
    argument values (as returned by argparse.parse_args()).

    """
    parser = argparse.ArgumentParser(description="Compile C files.")

    # The file name of the C file to compile.
    parser.add_argument("filename", metavar="filename")

    # Boolean flag for whether to print the generated IL
    parser.add_argument("-show-il", help="display generated IL",
                        dest="show_il", action="store_true")

    # Boolean flag for whether to print register allocator performance info
    parser.add_argument("-show-reg-alloc-perf",
                        help="display register allocator performance info",
                        dest="show_reg_alloc_perf", action="store_true")

    # Boolean flag for whether to allocate any variables in registers
    parser.add_argument("-variables-on-stack",
                        help="allocate all variables on the stack",
                        dest="variables_on_stack", action="store_true")

    parser.set_defaults(show_il=False)

    return parser.parse_args()


def read_file(arguments):
    """Read the file(s) in arguments and return the file contents."""
    try:
        with open(arguments.filename) as c_file:
            return c_file.read(), arguments.filename
    except IOError as e:
        descrip = "could not read file: '{}'"
        error_collector.add(CompilerError(descrip.format(arguments.filename)))


def write_asm(asm_source, asm_filename):
    """Save the given assembly source to disk at asm_filename.

    asm_source (str) - Full assembly source code.
    asm_filename (str) - Filename to which to save the generated assembly.

    """
    try:
        with open(asm_filename, "w") as s_file:
            s_file.write(asm_source)
    except IOError:
        descrip = "could not write output file '{}'"
        error_collector.add(CompilerError(descrip.format(asm_filename)))


def assemble_and_link(binary_name, asm_name, obj_name):
    """Assmble and link the assembly file into an object file and binary.

    If the assembly/linking fails, raise an exception. TODO: Deal with linker
    failures more smoothly.

    binary_name (str) - Name of the binary file to output
    asm_name (str) - Name of the assembly file to read in
    obj_name (str) - Name of the obj file to output

    """
    try:
        subprocess.check_call(["as", "-64", "-o", obj_name, asm_name])
    except subprocess.CalledProcessError:
        err = "assembler returned non-zero status"
        error_collector.add(CompilerError(err))
        return

    try:
        crtnum = find_crtnum()
        if not crtnum: return

        crti = find_library_or_err("crti.o")
        if not crti: return

        linux_so = find_library_or_err("ld-linux-x86-64.so.2")
        if not linux_so: return

        crtn = find_library_or_err("crtn.o")
        if not crtn: return

        # find files to link
        subprocess.check_call(
            ["ld", "-dynamic-linker", linux_so, crtnum, crti, "-lc",
             obj_name, crtn, "-o", binary_name])

    except subprocess.CalledProcessError:
        err = "linker returned non-zero status"
        error_collector.add(CompilerError(err))


def find_crtnum():
    """Search for the crt0, crt1, or crt2.o files on the system.

    If one is found, return its path. Else, add an error to the
    error_collector and return None.
    """
    for file in ["crt2.o", "crt1.o", "crt0.o"]:
        crt = find_library(file)
        if crt: return crt

    err = "could not find crt0.o, crt1.o, or crt2.o for linking"
    error_collector.add(CompilerError(err))
    return None


def find_library_or_err(file):
    """Search the given library file and return path if found.

    If not found, add an error to the error collector and return None.
    """
    path = find_library(file)
    if not path:
        err = "could not find {}".format(file)
        error_collector.add(CompilerError(err))
        return None
    else:
        return path


def find_library(file):
    """Search the given library file by searching in common directories.

    If found, returns the path. Otherwise, returns None.
    """
    search_paths = [pathlib.Path("/usr/local/lib/x86_64-linux-gnu"),
                    pathlib.Path("/lib/x86_64-linux-gnu"),
                    pathlib.Path("/usr/lib/x86_64-linux-gnu"),
                    pathlib.Path("/usr/local/lib64"),
                    pathlib.Path("/lib64"),
                    pathlib.Path("/usr/lib64"),
                    pathlib.Path("/usr/local/lib"),
                    pathlib.Path("/lib"),
                    pathlib.Path("/usr/lib"),
                    pathlib.Path("/usr/x86_64-linux-gnu/lib64"),
                    pathlib.Path("/usr/x86_64-linux-gnu/lib")]

    for path in search_paths:
        full = path.joinpath(file)
        if full.exists():
            return str(full)
    return None


if __name__ == "__main__":
    sys.exit(main())
