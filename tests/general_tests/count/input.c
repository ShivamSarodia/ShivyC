THIS IS THE TESTING INPUT FILE FOR THE COUNT.C PROGRAM. IT HAPPENS
TO BE COUNT.C ITSELF, FOR CONVENINCE. HOWEVER, SOME SMALL CHANGES
WERE MADE TO MAKE THIS A BETTER TEST.

TEST
TEST
TEST

/*******************************************************************************
 * Count.c                                                                     *
 * Shivam Sarodia - Yale University                                            *
 * Stanley Eisenstat, CS 223                                                   *
 *******************************************************************************/

#include <stdio.h>
#include <ctype.h>

// No arguments
// Always returns 0
// Takes program as input from stdin, outputs the input program with line nums
// Does not modify external state

int main()
{
  int c = 0; // current character
  int line_num = 0; // line number

  int p = 0; // last character
  int in_str = 0; // if we are in a string
  int in_char = 0; // if we are in a char string
  int in_cpp_comment = 0; // if we are in C++ comment
  int in_c_comment = 0; // if we are in a C comment
  int is_line = 0; // if current line is really a line
  int p_is_line = 0; // if it was a line character before
  int escaped = 0; // if the next character is to be escaped

  int p_else = 0; // if it was a line character before the else
  int else_state = 0; // counter to keep track of else letters

  while( (c = getchar()) != (-1) ) {
    // Check for line splices
    int next = getchar();
    if( (c == '\\') && (next == '\n') ) {
      putchar(c);
      putchar(next);
    }
    else {
      ungetc(next,stdin); // return next to stdin

      int ending_comment = 0; // if this character is used to end comment

      // check for C comment start
      if((p == '/') && (c == '*')
         && !in_str && !in_char && !in_cpp\
_comment ) {
        in_c_comment = 1;
        is_line = p_is_line;
      }

      // check for C comment end
      else if((p == '*') && (c == '/') ) {
        in_c_comment = 0;
        ending_comment = 1;
      }

      // check for C++ comment start
      else if((p == '/') && (c == '/')
              && !in_str && !in_char && !in_c_comment ) {
        in_cpp_comment = 1;
        is_line = p_is_line;
      }

      // check for string start
      else if((c == '"')
              && !in_char && !in_c_comment && !in_cpp_comment && !escaped)
        in_str = !in_str;

      // check for char string start
      else if((c == '\'')
              && !in_str && !in_c_comment && !in_cpp_comment && !escaped)
        in_char = !in_char;

      // check if the next char is escaped
      if(c == '\\') escaped = !escaped;
      else escaped = 0; // if not, the next character is not escaped

      p_is_line = is_line;
      p = c;

      // update is_line if this is a line of code
      if((c != '{') && (c != '}') && !isspace(c)
         && !in_c_comment && !in_cpp_comment
         && !ending_comment)
        is_line = 1;

      // deal with else
      if(c == 'e' && else_state == 0 && !in_c_comment && !in_cpp_comment) {
        p_else = p_is_line;
        else_state++;
      }
      else if(c == 'l' && else_state == 1) else_state++;
      else if(c == 's' && else_state == 2) else_state++;
      else if(c == 'e' && else_state == 3) {
        is_line = p_else;
        else_state = 0;
      }
      else else_state = 0;

      // if it's a newline that counts, print/reset stuff
      if(c == '\n' && is_line && !in_c_comment) {
        printf(" //%d", ++line_num);
        is_line = 0;
        // NO in_c_comment! do not reset in_c_comment
        p_is_line = 0;
        is_line = 0;
        p_else = 0;
      } else {

      }
      // if it's a newline at all, reset other stuff too
      if(c == '\n') in_cpp_comment = 0;\

      putchar(c);
    }\
  }

  return 0;
}
