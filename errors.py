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


class CompilerError(Exception):
    """Class representing compile-time errors.

    message (str) - User-friendly explanation of the error. Should
    begin with a lowercase letter.
    file_name (str) - File name in which the error occurred.
    line_number (int) - Line number on which the error occurred

    """

    def __init__(self, descrip, file_name=None, line_num=None, warning=False):
        """Initialize error.

        descrip (str) - Description of the error.
        file_name (str) - File in which the error appeared. If none is
        provided, uses "shivyc" when printing the message.
        line_num (int) - Line number of the file where the error appears.
        warning (bool) - True if this is a warning

        """
        self.descrip = descrip
        self.file_name = file_name
        self.line_num = line_num
        self.warning = warning

    def __str__(self):
        """Return a full representation of the error.

        The returned expression is user friendly and pretty-printable.

        """
        issue_type = "warning" if self.warning else "error"
        if self.file_name and self.line_num:
            return "{}:{}: {}: {}".format(self.file_name, self.line_num,
                                          issue_type, self.descrip)
        elif self.file_name:
            return "{}: {}: {}".format(self.file_name, issue_type,
                                       self.descrip)
        else:
            return "shivyc: {}: {}".format(issue_type, self.descrip)


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
                             tokens[index].file_name, tokens[index].line_num)
        elif message_type == self.GOT:
            super().__init__("{}, got '{}'".format(message, tokens[index]),
                             tokens[index].file_name, tokens[index].line_num)
        elif message_type == self.AFTER:
            super().__init__(
                "{} after '{}'".format(message, tokens[index - 1]),
                tokens[index - 1].file_name, tokens[index - 1].line_num)
        else:
            raise ValueError("Unknown error message type")
