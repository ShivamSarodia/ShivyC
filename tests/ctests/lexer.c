// Test various lexer edge cases

int strcmp(char*, char*);

int main() {
  char* a = "he\
l\
  lo//"\
            ;

  if(strcmp(a, "hel  lo//")) return 1;

  /\
/ this is a comment

  return 0;
}\
