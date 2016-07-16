#!/usr/bin/env python3

"""Main executable for ShivyC compiler

For usage, run "./shivyc.py --help".

"""

import argparse
import subprocess

from code_gen import CodeStore
from lexer import Lexer
from parser import Parser
import token_kinds

def main():
    """Load the input files and dispatch to the compile function for the main
    processing.

    The main function handles interfacing with the user, like reading the
    command line arguments, printing errors, and generating output files. The
    compilation logic is in the compile_code function to facilitate testing.

    """
    arguments = get_arguments()

    try:
        c_file = open(arguments.file_name)
    except IOError:
        # TODO: return errors in a universal way
        print("shivyc: error: no such file or directory: '{}'"
              .format(arguments.file_name))
        return

    try:
        c_source = c_file.read()
    except IOError:
        # TODO: return errors in a universal way
        print("shivyc: error: cannot read file '{}'"
              .format(arguments.file_name))
        c_file.close()
        return
    c_file.close()
    
    try:
        s_source = compile_code(c_source)
    except NotImplementedError:
        # TODO: return errors in a universal way
        print("shivyc: error: NotImplementedError")
        return
    
    try:
        s_file = open("out.s", "w")
    except IOError:
        # TODO: return errors in a universal way
        print("shivyc: error: cannot open output file '{}'"
              .format("out.s"))
        return
        
    try:
        s_file.write(s_source)
    except IOError:
        # TODO: return errors in a universal way
        print("shivyc: error: cannot write output file '{}'"
              .format("out.s"))
        s_file.close()
        return
    s_file.close()

    # TODO: return errors in a universal way
    subprocess.run(["nasm", "-f", "elf64", "-o", "out.o", "out.s"]).check_returncode()
    subprocess.run(["ld", "out.o", "-o", "out"]).check_returncode()

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

def compile_code(source):
    """Compile the provided source code into assembly.

    source (str) - The C source code to compile.
    return (str) - The asm output

    """
    lexer = Lexer(token_kinds.symbol_kinds, token_kinds.keyword_kinds)
    token_list = lexer.tokenize(source)

    parser = Parser()
    ast_root = parser.parse(token_list)

    code_store = CodeStore()
    ast_root.make_code(code_store)

    return code_store.full_code()

if __name__ == "__main__":
    main()
