int isalpha(int);

// This declaration differs from the C standard library, but it allows us to
// verify that a void parameter works.
int isdigit(void);

struct S incomplete_return();

int main() {
  int a;

  // error: called object is not a function pointer
  a();

  // error: incorrect number of arguments for function call (expected 1, have 0)
  isalpha();

  // error: incorrect number of arguments for function call (expected 1, have 2)
  isalpha(10, 10);

  isdigit();

  // error: incorrect number of arguments for function call (expected 0, have 1)
  isdigit(1);

  // error: incorrect number of arguments for function call (expected 0, have 2)
  isdigit(1, 2);

  // error: function returns non-void incomplete type
  incomplete_return();

  return 0;
}
