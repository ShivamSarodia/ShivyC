int main() {
  // Issue: 3: error: expression on left of '=' is not assignable
  3 = 4;

  int a;
  // Issue: 7: error: expression on left of '=' is not assignable
  3 = a;

  // Issue: 10: error: expression on left of '=' is not assignable
  3 + 4 = a;

  // Issue: 13: error: expression on left of '=' is not assignable
  a + a = 3;

  // Issue: 16: error: expression on left of '=' is not assignable
  a = (5 = 6);

  return 0;
}
