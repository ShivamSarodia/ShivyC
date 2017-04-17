int main() {
  int array[5];

  // Issue: 5: error: expression on left of '=' is not assignable
  array = 4;

  // Issue: 8: error: invalid operand types for array subscriping
  4[3];

  // Issue: 11: error: invalid operand types for array subscriping
  array[array];

  // Issue: 14: error: declared variable is not of assignable type
  int array1[5] = 1;
}
