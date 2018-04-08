int add(int a, int b) {
  return 0;
}

void test_no_args() { }

int main() {
  // error: incorrect number of arguments for function call (expected 2, have 3)
  add(1,2,3);

  char* p;
  // error: invalid conversion between types
  add(1, p);

  // error: incorrect number of arguments for function call (expected 0, have 1)
  test_no_args(1);
}
