"""Main executable for ShivyC compiler."""

import argparse
import pathlib
import platform
import subprocess
import sys

import shivyc.lexer as lexer
import shivyc.preproc as preproc

from shivyc.errors import error_collector, CompilerError
from shivyc.parser.parser import parse
from shivyc.il_gen import ILCode, SymbolTable, Context
from shivyc.asm_gen import ASMCode, ASMGen


def main():
    """Run the main compiler script."""

    if platform.system() != "Linux":
        err = "only x86_64 Linux is supported"
        print(CompilerError(err))
        return 1

    arguments = get_arguments()

    objs = []
    for file in arguments.files:
        objs.append(process_file(file, arguments))

    error_collector.show()
    if any(not obj for obj in objs):
        return 1
    else:
        if not link("out", objs):
            err = "linker returned non-zero status"
            print(CompilerError(err))
            return 1
        return 0


def process_file(file, args):
    """Process single file into object file and return the object file name."""
    if file[-2:] == ".c":
        return process_c_file(file, args)
    elif file[-2:] == ".o":
        return file
    else:
        err = f"unknown file type: '{file}'"
        error_collector.add(CompilerError(err))
        return None


def process_c_file(file, args):
    """Compile a C file into an object file and return the object file name."""
    code = read_file(file)
    if not error_collector.ok():
        return None

    token_list = lexer.tokenize(code, file)
    if not error_collector.ok():
        return None

    token_list = preproc.process(token_list, file)
    if not error_collector.ok():
        return None

    # If parse() can salvage the input into a parse tree, it may emit an
    # ast_root even when there are errors saved to the error_collector. In this
    # case, we still want to continue the compiler stages.
    ast_root = parse(token_list)
    if not ast_root:
        return None

    il_code = ILCode()
    symbol_table = SymbolTable()
    ast_root.make_il(il_code, symbol_table, Context())
    if not error_collector.ok():
        return None

    asm_code = ASMCode()
    ASMGen(il_code, symbol_table, asm_code, args).make_asm()
    asm_source = asm_code.full_code()
    if not error_collector.ok():
        return None

    asm_file = file[:-2] + ".s"
    obj_file = file[:-2] + ".o"

    write_asm(asm_source, asm_file)
    if not error_collector.ok():
        return None

    assemble(asm_file, obj_file)
    if not error_collector.ok():
        return None

    return obj_file


def get_arguments():
    """Get the command-line arguments.

    This function sets up the argument parser. Returns a tuple containing
    an object storing the argument values and a list of the file names
    provided on command line.
    """
    desc = """Compile, assemble, and link C files. Option flags starting
    with `-z` are primarily for debugging or diagnostic purposes."""
    parser = argparse.ArgumentParser(
        description=desc, usage="shivyc [-h] [options] files...")

    # Files to compile
    parser.add_argument("files", metavar="files", nargs="+")

    # Boolean flag for whether to print register allocator performance info
    parser.add_argument("-z-reg-alloc-perf",
                        help="display register allocator performance info",
                        dest="show_reg_alloc_perf", action="store_true")

    return parser.parse_args()


def read_file(file):
    """Return the contents of the given file."""
    try:
        with open(file) as c_file:
            return c_file.read()
    except IOError as e:
        descrip = f"could not read file: '{file}'"
        error_collector.add(CompilerError(descrip))


def write_asm(asm_source, asm_filename):
    """Save the given assembly source to disk at asm_filename.

    asm_source (str) - Full assembly source code.
    asm_filename (str) - Filename to which to save the generated assembly.

    """
    try:
        with open(asm_filename, "w") as s_file:
            s_file.write(asm_source)
    except IOError:
        descrip = f"could not write output file '{asm_filename}'"
        error_collector.add(CompilerError(descrip))


def assemble(asm_name, obj_name):
    """Assemble the given assembly file into an object file."""
    try:
        subprocess.check_call(["as", "-64", "-o", obj_name, asm_name])
        return True
    except subprocess.CalledProcessError:
        err = "assembler returned non-zero status"
        error_collector.add(CompilerError(err))
        return False


def link(binary_name, obj_names):
    """Assemble the given object files into a binary."""

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
            ["ld", "-dynamic-linker", linux_so, crtnum, crti, "-lc"]
            + obj_names + [crtn, "-o", binary_name])

        return True

    except subprocess.CalledProcessError:
        return False


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
        err = f"could not find {file}"
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
        if full.is_file():
            return str(full)
    return None


if __name__ == "__main__":
    sys.exit(main())
