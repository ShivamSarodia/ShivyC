int main() {
  // error: expression on left of '=' is not assignable
  3 = 4;

  int a;
  // error: expression on left of '=' is not assignable
  3 = a;

  // error: expression on left of '=' is not assignable
  3 + 4 = a;

  // error: expression on left of '=' is not assignable
  a + a = 3;

  // error: expression on left of '=' is not assignable
  a = (5 = 6);

  return 0;
}
