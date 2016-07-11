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

    # The C file to compile
    parser.add_argument("file_name")
    return parser.parse_args()

def main():
    """Run the compiler

    """
    arguments = get_arguments()
    print(arguments)

if __name__ == "__main__":
    main()
