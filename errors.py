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
        self.end = end if end else start


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

            insert = [bold_color,
                      self.range.start.file,
                      self.range.start.line,
                      self.range.start.col,
                      color_code,
                      issue_type,
                      reset_color,
                      self.descrip,
                      self.range.start.full_line,
                      indicator]

            return "{}{}:{}:{}: {}{}:{} {}\n  {}\n  {}".format(*insert)

        # A position range is not provided and this is output to terminal.
        else:
            insert = [bold_color,
                      color_code,
                      issue_type,
                      reset_color,
                      self.descrip]
            return "{}shivyc: {}{}:{} {}".format(*insert)


class ParserError(CompilerError):
    """Class representing parser errors.

    amount_parsed (int) - Number of tokens successfully parsed before this
    error was encountered. This value is used by the Parser to determine which
    error corresponds to the most successful parse.

    """

    # Options for the message_type constructor field.
    #
    # AT generates a message like "expected semicolon at '}'", GOT generates a
    # message like "expected semicolon, got '}'", and AFTER generates a message
    # like "expected semicolon after '15'" (if possible).
    #
    # As a very general guide, use AT when a token should be removed, use AFTER
    # when a token should be to be inserted (esp. because of what came before),
    # and GOT when a token should be changed.
    AT = 1
    GOT = 2
    AFTER = 3

    def __init__(self, message, index, tokens, message_type):
        """Initialize a ParserError from the given arguments.

        message (str) - Base message to put in the error.
        tokens (List[Token]) - List of tokens.
        index (int) - Index of the offending token.
        message_type (int) - One of self.AT, self.GOT, or self.AFTER.

        Example:
            ParserError("unexpected semicolon", 10, [...], self.AT)
               -> CompilerError("unexpected semicolon at ';'", ..., ...)
               -> "main.c:10: unexpected semicolon at ';'"
        """
        self.amount_parsed = index

        if len(tokens) == 0:
            super().__init__("{} at beginning of source".format(message))

        # If the index is too big, we're always using the AFTER form
        if index >= len(tokens):
            index = len(tokens)
            message_type = self.AFTER
        # If the index is too small, we should not use the AFTER form
        elif index <= 0:
            index = 0
            if message_type == self.AFTER:
                message_type = self.GOT

        if message_type == self.AT:
            super().__init__("{} at '{}'".format(message, tokens[index]),
                             tokens[index].r)
        elif message_type == self.GOT:
            super().__init__("{}, got '{}'".format(message, tokens[index]),
                             tokens[index].r)
        elif message_type == self.AFTER:
            if tokens[index - 1].r:
                new_range = Range(tokens[index - 1].r.end + 1)
            else:
                new_range = None

            super().__init__(
                "{} after '{}'".format(message, tokens[index - 1]), new_range)
