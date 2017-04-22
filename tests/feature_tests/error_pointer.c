 int main() {
  int a; int b;

  // Issue: 5: error: lvalue required as unary '&' operand
  &(a + b);

  // Issue: 8: error: operand of unary '*' must have pointer type
  *a;

  // Issue: 11: error: invalid conversion between types
  a = &b;  // setting integer to pointer

  // Issue: 15: error: invalid conversion between types
  int* c;
  c = 10;  // setting pointer to integer

  // Issue: 18: error: operand of unary '*' must have pointer type
  *a = 1;

  return 0;
 }
