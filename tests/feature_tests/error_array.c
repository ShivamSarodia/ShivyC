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
}
