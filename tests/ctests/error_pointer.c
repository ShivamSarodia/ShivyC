int main() {
  int a; int b;

  // Issue: 5: error: lvalue required as unary '&' operand
  &(a + b);

  // Issue: 8: error: operand of unary '*' must have pointer type
  *a;

  return 0;
}
