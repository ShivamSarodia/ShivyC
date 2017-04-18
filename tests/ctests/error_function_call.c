int isalpha(int);

// This declaration differs from the C standard library, but it allows us to
// verify that a void parameter works.
int isdigit(void);

int main() {
  int a;

  // Issue: 11: error: called object is not a function pointer
  a();

  // Issue: 14: error: incorrect number of arguments for function call
  isalpha();

  // Issue: 17: error: incorrect number of arguments for function call
  isalpha(10, 10);

  isdigit();

  // Issue: 22: error: incorrect number of arguments for function call
  isdigit(1);

  // Issue: 25: error: incorrect number of arguments for function call
  isdigit(1, 2);

  return 0;
}
