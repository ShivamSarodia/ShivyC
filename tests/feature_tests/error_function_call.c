int isalpha(int);

// This declaration differs from the C standard library, but it allows us to
// verify that a void parameter works.
int isdigit(void);

int main() {
  int a;

  // error: called object is not a function pointer
  a();

  // error: incorrect number of arguments for function call
  isalpha();

  // error: incorrect number of arguments for function call
  isalpha(10, 10);

  isdigit();

  // error: incorrect number of arguments for function call
  isdigit(1);

  // error: incorrect number of arguments for function call
  isdigit(1, 2);

  return 0;
}
