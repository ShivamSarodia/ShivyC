class CompilerError(Exception):
    """Used to report compile-time errors. These should be caught and
    pretty-printed for the user.
    
    message (str) - a user-friendly explanation of the error
    file_name (str) - the file name in which the error occurred
    line_number (int) - the line on which the error occurred
    context (str) - the context around which the error occurred

    """
    def __init__(self, descrip, file_name = None, line_number = None,
                 context = None):
        self.descrip = descrip
        self.file_name = file_name
        self.line_number = line_number
        self.context = context
        
    def __str__(self):
        if self.file_name and self.line_number:
            prefix = "{0}:{1}: error:".format(
                self.file_name, self.line_number)
        elif self.file_name:
            prefix = "{0}: error:".format(self.file_name)
        else:
            prefix = "shivyc: error: "

        return prefix + self.descrip + ("\n    " + self.context
                                        if self.context else "")
