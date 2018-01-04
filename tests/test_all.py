"""Integration test driver for the compiler.

This module defines metaclassis which generate test cases from files on disk,
and a test class based off that metaclass. For each file that matches
"tests/feature_tests/*.c", a feature test function is generated, and for
each file that matches "tests/frontend_tests/*.c", a frontend test function
is generated.

If the C file contains a line of the form:

// Return: ###

Then, the test expects the main() in that test file to return the value
"###". If no such line exists, the default expected return value is 0.

If the C file contains line(s) of the form:

// error: ____
// warning: ____

Then, the test expects compilation to raise an error or warning on the
following line whose message is the string "____".
"""

import glob
import pathlib
import subprocess
import unittest

import shivyc.main
from shivyc.errors import error_collector


def compile_with_shivyc(test_file_name):
    """Compile given file with ShivyC.

    Errors are saved in the error collector.

    """
    # Mock out arguments to ShivyC call
    class MockArguments:
        files = [test_file_name]
        show_reg_alloc_perf = False
        variables_on_stack = False

    shivyc.main.get_arguments = lambda: MockArguments()

    # Mock out error collector functions
    error_collector.show = lambda: True

    shivyc.main.main()


def _read_params(test_file_name):
    """Return expected errors, warnings, and return value for test file."""

    with open(test_file_name) as f:
        exp_ret_val = 0
        exp_errors = []
        exp_warnings = []

        for index, line in enumerate(f.readlines()):
            ret_mark = "// Return:"
            error_mark = "// error:"
            warning_mark = "// warning:"

            if line.strip().startswith(ret_mark):
                exp_ret_val = int(line.split(ret_mark)[-1])
            elif line.strip().startswith(error_mark):
                error_text = line.split(error_mark)[-1].strip()
                exp_errors.append((error_text, index + 2))
            elif line.strip().startswith(warning_mark):
                warning_text = line.split(warning_mark)[-1].strip()
                exp_warnings.append((warning_text, index + 2))

    return exp_errors, exp_warnings, exp_ret_val


def generate_test(test_file_name):
    """Return a function that tests given file."""

    def test_function(self):
        exp_errors, exp_warnings, exp_ret_val = _read_params(test_file_name)

        compile_with_shivyc(test_file_name)

        act_errors = []
        act_warnings = []

        for issue in error_collector.issues:
            issue_list = act_warnings if issue.warning else act_errors
            issue_list.append((issue.descrip, issue.range.start.line))

        self.assertListEqual(act_errors, exp_errors)
        self.assertListEqual(act_warnings, exp_warnings)

        if not act_errors:
            self.assertEqual(subprocess.call(["./out"]), exp_ret_val)

    return test_function


def new(glob_str, dct):
    """The implementation of __new__ used for generating tests."""
    test_file_name = glob.glob(glob_str)
    for test_file_name in test_file_name:
        short_name = test_file_name.split("/")[-1][:-2]
        test_func_name = "test_" + short_name
        dct[test_func_name] = generate_test(test_file_name)


class TestUtils(unittest.TestCase):
    """Helper base class for all unit tests."""

    def setUp(self):
        """Clear error collector before each test."""
        error_collector.clear()


class MetaFrontendTests(type):
    """Metaclass for creating frontend tests."""

    def __new__(meta, name, bases, dct):
        """Create FrontendTests class."""
        new("tests/frontend_tests/*.c", dct)
        return super().__new__(meta, name, bases, dct)


class FrontendTests(TestUtils, metaclass=MetaFrontendTests):
    """Frontend tests that test the lexer, preprocessor, and parser."""

    pass


class MetaFeatureTests(type):
    """Metaclass for creating feature tests."""

    def __new__(meta, name, bases, dct):
        """Create FeatureTests class."""
        new("tests/feature_tests/*.c", dct)
        done_class = super().__new__(meta, name, bases, dct)
        return done_class


class FeatureTests(TestUtils, metaclass=MetaFeatureTests):
    """Frontend tests that test the lexer, preprocessor, and parser."""

    pass


class IntegrationTests(TestUtils):
    """Integration tests for the compiler.

    These test the programs found in general_tests/* for proper functionality.
    """

    def io_test(self, rel_dir, cfile, stdin):
        """Run a general I/O test.

        Args:
            name (str): Name of this test
            rel_dir (str): Directory for the test
            cfile (str): The .c file to compile and run
            stdin (str): The file to pipe into stdin of the executable, or None
        """
        dir = str(pathlib.Path(__file__).parent.joinpath(rel_dir))

        # Remove leftover files from last test
        rm = "rm -f {0}/gcc_out {0}/out {0}/shivyc_output {0}/gcc_output"
        subprocess.run(rm.format(dir), shell=True, check=True)

        # Compile with ShivyC
        compile_with_shivyc(str(pathlib.Path(dir).joinpath(cfile)))
        self.assertEqual(error_collector.issues, [])

        # Compile with gcc
        gcc_compile = "gcc -std=c11 {0}/{1} -o gcc_out".format(dir, cfile)
        subprocess.run(gcc_compile, shell=True, check=True)

        # Run ShivyC executable on sample input
        if stdin:
            shivyc_run = "./out < {0}/input.c > {0}/shivyc_output".format(dir)
            gcc_run = "./gcc_out < {0}/input.c > {0}/gcc_output".format(dir)
        else:
            shivyc_run = "./out > {0}/shivyc_output".format(dir)
            gcc_run = "./gcc_out > {0}/gcc_output".format(dir)

        subprocess.run(shivyc_run, shell=True, check=True)
        subprocess.run(gcc_run, shell=True, check=True)

        # Diff the two output files
        diff = "diff {0}/gcc_output {0}/shivyc_output".format(dir)
        subprocess.run(diff, shell=True, check=True)

    def test_count(self):
        """Test the Count.c program from the first pset of CPSC 223 at Yale."""

        self.io_test("general_tests/count", "Count.c", "input.c")

    def test_pi(self):
        """Test the pi.c program."""

        self.io_test("general_tests/pi", "pi.c", None)
