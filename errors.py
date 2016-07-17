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
