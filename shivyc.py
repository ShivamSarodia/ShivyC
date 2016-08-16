#!/usr/bin/env python3
"""Main executable for ShivyC compiler.

For usage, run "./shivyc.py --help".

"""

import argparse
import subprocess

import token_kinds
from errors import CompilerError
from lexer import Lexer
from parser import Parser
from il_gen import ILCode
from il_gen import SymbolTable
from asm_gen import ASMCode
from asm_gen import ASMGen


def main():
    """Load the input files, compile them, and save output.

    The main function handles interfacing with the user, like reading the
    command line arguments, printing errors, and generating output files.

    """
    arguments = get_arguments()

    try:
        with open(arguments.file_name) as c_file:
            code_lines = [
                (line_text.strip(), arguments.file_name, line_num + 1)
                for line_num, line_text in enumerate(c_file)
            ]
    except IOError:
        raise CompilerError("could not read file: '{}'"
                            .format(arguments.file_name))

    asm_source = compile_to_asm(code_lines)
    asm_filename = "out.s"
    write_asm(asm_source, asm_filename)

    assemble_and_link("out", asm_filename, "out.o")


def get_arguments():
    """Get the command-line arguments.

    This function sets up the argument parser and returns an object storing the
    argument values (as returned by argparse.parse_args()).

    """
    parser = argparse.ArgumentParser(description="Compile C files.")

    # The file name of the C file to compile. The file name gets saved to the
    # file_name attribute of the returned object, but this parameter appears as
    # "filename" (no underscore) on the command line.
    parser.add_argument("file_name", metavar="filename")
    return parser.parse_args()


def compile_to_asm(code_lines):
    """Compile the given code lines to asm.

    code_lines (List(tuple)) - Lines of code. First element is the line of code
    itself, second element is the file name, third element is the line number.

    """
    lexer = Lexer(token_kinds.symbol_kinds, token_kinds.keyword_kinds)
    token_list = lexer.tokenize(code_lines)

    ast_root = Parser(token_list).parse()

    il_code = ILCode()
    symbol_table = SymbolTable()
    ast_root.make_code(il_code, symbol_table)

    asm_code = ASMCode()
    ASMGen(il_code, asm_code).make_asm()

    return asm_code.full_code()


def write_asm(asm_source, asm_filename):
    """Save the given assembly source to disk at asm_filename.

    asm_source (str) - Full assembly source code.
    asm_filename (str) - Filename to which to save the generated assembly.

    """
    try:
        with open(asm_filename, "w") as s_file:
            s_file.write(asm_source)
    except IOError:
        raise CompilerError("could not write output file '{}'".format(
            asm_filename))


def assemble_and_link(binary_name, asm_name, obj_name):
    """Assmble and link the assembly file into an object file and binary.

    If the assembly/linking fails, raise an exception. TODO: Deal with linker
    failures more smoothly.

    binary_name (str) - Name of the binary file to output
    asm_name (str) - Name of the assembly file to read in
    obj_name (str) - Name of the obj file to output

    """
    subprocess.check_call(["nasm", "-f", "elf64", "-o", obj_name, asm_name])
    subprocess.check_call([
        "ld", "-dynamic-linker", "/lib64/ld-linux-x86-64.so.2",
        "/usr/lib/x86_64-linux-gnu/crt1.o", "/usr/lib/x86_64-linux-gnu/crti.o",
        "-lc", obj_name, "/usr/lib/x86_64-linux-gnu/crtn.o", "-o", binary_name
    ])


if __name__ == "__main__":
    try:
        main()
    except CompilerError as e:
        print(e)
