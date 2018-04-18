int func(void);

struct S;

int main() {
  int array[5];

  // error: expression on left of '=' is not assignable
  array = 4;

  // error: invalid operand types for array subscriping
  4[3];

  // error: invalid operand types for array subscriping
  array[array];

  // error: declared variable is not of assignable type
  int array1[5] = 1;

  void* p;
  // error: cannot subscript pointer to incomplete type
  p[4];

  // error: array size must be compile-time constant
  int array1[func()];

  // error: array size must have integral type
  int array2[(int*)1];

  // error: array size must be positive
  int array3[-2];

  // error: array elements must have complete type
  struct S array4[3];

  // error: array elements must have complete type
  int array5[3][];
}
