int main() {
  int* a; int *b;

  // Issue: 5: error: invalid operand types for binary addition
  a + b;

  // Issue: 8: error: invalid operand types for binary multiplication
  a * b;

  // Issue: 11: error: invalid operand types for binary division
  a / b;

  // Issue: 14: error: invalid operand types for binary subtraction
  3 - a;
}
