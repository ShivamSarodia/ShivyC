struct S { int a; } s;

int main() {
  int* a; int *b;

  // error: invalid operand types for addition
  a + b;

  // error: invalid operand types for multiplication
  a * b;

  // error: invalid operand types for division
  a / b;

  // error: invalid operand types for modulus
  a % b;

  // error: invalid operand types for modulus
  3 % b;

  // error: invalid operand types for subtraction
  3 - a;

  // error: invalid operand types for bitwise shift
  int* c; c << 3;

  void *p, *q;
  // error: invalid arithmetic on pointer to incomplete type
  p + 1;
  // error: invalid arithmetic on pointer to incomplete type
  1 + p;
  // error: invalid arithmetic on pointers to incomplete types
  p - q;
  // error: invalid arithmetic on pointer to incomplete type
  p - 1;
  // error: invalid arithmetic on pointer to incomplete type
  p++;
  // error: invalid type for increment operator
  s++;
}
