#!/usr/bin/env python3

"""Main executable for ShivyC compiler

For usage, run "./shivyc.py --help".

"""

import argparse

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

def main():
    """Run the compiler

    """
    arguments = get_arguments()
    print(arguments)

if __name__ == "__main__":
    main()
