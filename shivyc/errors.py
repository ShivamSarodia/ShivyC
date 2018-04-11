"""Objects used for error reporting.

The main executable catches an exception and prints it for the user.

"""


class ErrorCollector:
    """Class that accumulates all errors and warnings encountered.

    We create a global instance of this class so all parts of the compiler can
    access it and add errors to it. This is kind of janky, but it's much easier
    than passing an instance to every function that could potentially fail.

    """

    def __init__(self):
        """Initialize the ErrorCollector with no issues to report."""
        self.issues = []

    def add(self, issue):
        """Add the given error or warning (CompilerError) to list of errors."""
        self.issues.append(issue)
        self.issues.sort()

    def ok(self):
        """Return True iff there are no errors."""
        return not any(not issue.warning for issue in self.issues)

    def show(self):  # pragma: no cover
        """Display all warnings and errors."""
        for issue in self.issues:
            print(issue)

    def clear(self):
        """Clear all warnings and errors. Intended only for testing use."""
        self.issues = []


error_collector = ErrorCollector()


class Position:
    """Class representing a position in source code.

    file (str) - Name of file in which this position is located.
    line (int) - Line number in file at which this position is located.
    col (int) - Horizontal column at which this position is located
    full_line (str) - Full text of the line containing this position.
    Specifically, full_line[col + 1] should be this position.
    """

    def __init__(self, file, line, col, full_line):
        """Initialize Position object."""
        self.file = file
        self.line = line
        self.col = col
        self.full_line = full_line

    def __add__(self, other):
        """Increment Position column by one."""
        return Position(self.file, self.line, self.col + 1, self.full_line)


class Range:
    """Class representing a continuous range between two positions.

    start (Position) - start position, inclusive
    end (Position) - end position, inclusive
    """

    def __init__(self, start, end=None):
        """Initialize Range objects."""
        self.start = start
        self.end = end or start

    def __add__(self, other):
        """Add Range objects by concatenating their ranges."""
        return Range(self.start, other.end)


class CompilerError(Exception):
    """Class representing compile-time errors.

    message (str) - User-friendly explanation of the error. Should
    begin with a lowercase letter.
    file_name (str) - File name in which the error occurred.
    line_number (int) - Line number on which the error occurred

    """

    def __init__(self, descrip, range=None, warning=False):
        """Initialize error.

        descrip (str) - Description of the error.
        range (Range) - Range at which the error appears.
        warning (bool) - True if this is a warning

        """
        self.descrip = descrip
        self.range = range
        self.warning = warning

    def __str__(self):  # pragma: no cover
        """Return a pretty-printable statement of the error.

        Also includes the line on which the error occurred.
        """
        error_color = "\x1B[31m"
        warn_color = "\x1B[33m"
        reset_color = "\x1B[0m"
        bold_color = "\033[1m"

        color_code = warn_color if self.warning else error_color
        issue_type = "warning" if self.warning else "error"

        # A position range is provided, and this is output to terminal.
        if self.range:

            # Set "indicator" to display the ^^^s and ---s to indicate the
            # error location.
            indicator = warn_color
            indicator += " " * (self.range.start.col - 1)

            if (self.range.start.line == self.range.end.line and
                 self.range.start.file == self.range.end.file):

                if self.range.end.col == self.range.start.col:
                    indicator += "^"
                else:
                    indicator += "-" * (self.range.end.col -
                                        self.range.start.col + 1)

            else:
                indicator += "-" * (len(self.range.start.full_line) -
                                    self.range.start.col + 1)

            indicator += reset_color
            return (f"{bold_color}{self.range.start.file}:"
                    f"{self.range.start.line}:{self.range.start.col}: "
                    f"{color_code}{issue_type}:{reset_color} {self.descrip}\n"
                    f"  {self.range.start.full_line}\n"
                    f"  {indicator}")
        # A position range is not provided and this is output to terminal.
        else:
            return (f"{bold_color}shivyc: {color_code}{issue_type}:"
                    f"{reset_color} {self.descrip}")

    def __lt__(self, other):  # pragma: no cover
        """Provides sort order for printing errors."""

        # everything without a range comes before everything with range
        if not self.range:
            return bool(other.range)

        # no opinion between errors in different files
        if self.range.start.file != other.range.start.file:
            return False

        this_tuple = self.range.start.line, self.range.start.col
        other_tuple = other.range.start.line, other.range.start.col
        return this_tuple < other_tuple
