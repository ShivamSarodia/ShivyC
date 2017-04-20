// Test various lexer edge cases

int strcmp(char*, char*);

int main() {
  char*/*strange comment*/a = "he\
l\
  lo///*"\
            ;

  if(strcmp(a, "hel  lo///*")) return 1;

  /\
/ this is a comment

  int b = 3;

  "*/";
  // /*
  /* // */
  /* /* */  b = 4;

  /*

    b = 5;


  */


  if(b != 4) return 2;

  return 0;
}\
