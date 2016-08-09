class CompilerError(Exception):
    """Used to report compile-time errors. These should be caught and
    pretty-printed for the user.
    
    message (str) - a user-friendly explanation of the error
    file_name (str) - the file name in which the error occurred
    line_number (int) - the line on which the error occurred
    context (str) - the context around which the error occurred

    """
    def __init__(self, descrip, file_name = None, line_num = None):
        self.descrip = descrip
        self.file_name = file_name
        self.line_num = line_num
        
    def __str__(self):
        if self.file_name and self.line_num:
            return "{}:{}: error: {}".format(
                self.file_name, self.line_num, self.descrip)
        elif self.file_name:
            return "{}: error: {}".format(self.file_name, self.descrip)
        else:
            return "shivyc: error: {}".format(self.descrip)

def token_error(descrip, token):
    """Returns a CompilerError with based on the given description and token.

    descrip (string) - a string containing '{}' where the token content should
    be inserted
    token (Token) - the token for which an error is being reported
    """
    return CompilerError(descrip.format(str(token)), token.file_name,
                         token.line_num)

class ParserError(CompilerError):
    """Used to report parser errors. These are caught and pretty-printed
    for the user in the main module.
    """
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
        """Initializes a ParserError from the given arguments.

        message (str) - the base message to put in the error
        tokens (List[Token]) - a list of tokens
        index (int) - the index of the offending token
        message_type (int) - either self.AT, self.GOT, or self.AFTER. 
        """
        if len(tokens) == 0:
            super().__init__("{} at beginning of source".format(message))

        # If the index is too big, we're always using the AFTER form
        if index >= len(tokens):
            index = len(tokens)
            message_type = self.AFTER
        # If the index is too small, we should not use the AFTER form
        elif index <= 0:
            index = 0
            if message_type == self.AFTER: message_type = self.GOT

        if message_type == self.AT:
            super().__init__("{} at '{}'".format(message, tokens[index]),
                             tokens[index].file_name, tokens[index].line_num)
        elif message_type == self.GOT:
            super().__init__("{}, got '{}'".format(message, tokens[index]),
                             tokens[index].file_name, tokens[index].line_num)
        elif message_type == self.AFTER:
            super().__init__("{} after '{}'".format(message, tokens[index-1]),
                             tokens[index-1].file_name,
                             tokens[index-1].line_num)
        else:
            raise ValueError("Unknown error message type")
