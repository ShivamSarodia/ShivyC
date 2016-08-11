#!/usr/bin/env python3

"""Main executable for ShivyC compiler

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

def main():
    """Load the input files and dispatch to the compile function for the main
    processing.

    The main function handles interfacing with the user, like reading the
    command line arguments, printing errors, and generating output files. The
    compilation logic is in the compile_code function to facilitate testing.

    """
    arguments = get_arguments()

    try:
        with open(arguments.file_name) as c_file:
            code_lines = [(line_text.strip(), arguments.file_name, line_num+1)
                          for line_num, line_text in enumerate(c_file)]
    except IOError:
        raise CompilerError("could not read file: '{}'"
                            .format(arguments.file_name))

    # Compile the code
    lexer = Lexer(token_kinds.symbol_kinds, token_kinds.keyword_kinds)
    token_list = lexer.tokenize(code_lines)

    ast_root = Parser(token_list).parse()

    il_code = ILCode()
    symbol_table = SymbolTable()
    ast_root.make_code(il_code, symbol_table)
    print(il_code)
    raise NotImplementedError("IL->ASM phase still in construction")

    try:
        with open("out.s", "w") as s_file:
            s_file.write(s_source)
    except IOError:
        raise CompilerError("could not write output file '{}'"
                            .format("out.s"))

    assemble_and_link("out", "out.s", "out.o")

def get_arguments():
    """Set up the argument parser and return an object storing the
    argument values.

    return - An object storing argument values, as returned by
    argparse.parse_args()

    """

    parser = argparse.ArgumentParser(description="Compile C files.")

    # The file name of the C file to compile. The file name gets saved to the
    # file_name attribute of the returned object, but this parameter appears as
    # "filename" (no underscore) on the command line.
    parser.add_argument("file_name", metavar="filename")
    return parser.parse_args()

def assemble_and_link(binary_name, asm_name, obj_name):
    """Assmble and link the assembly file into an object file and
    binary. If the assembly/linking fails, raise an exception.

    binary_name (str) - name of the binary file to output
    asm_name (str) - name of the assembly file to read in
    obj_name (str) - name of the obj file to output

    """
    subprocess.run(["nasm", "-f", "elf64", "-o", obj_name,
                    asm_name]).check_returncode()
    subprocess.run(["ld", "-dynamic-linker", "/lib64/ld-linux-x86-64.so.2",
                    "/usr/lib/x86_64-linux-gnu/crt1.o",
                    "/usr/lib/x86_64-linux-gnu/crti.o", "-lc", obj_name,
                    "/usr/lib/x86_64-linux-gnu/crtn.o", "-o",
                    binary_name]).check_returncode()
    
if __name__ == "__main__":
    try:
        main()
    except CompilerError as e:
        print(e)
