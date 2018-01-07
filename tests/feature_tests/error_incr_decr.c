int main() {
  // error: operand of decrement operator not a modifiable lvalue
  4--;

  int array[5];
  // error: operand of increment operator not a modifiable lvalue
  ++array;

  void* p;
  // error: operand of increment operator not a modifiable lvalue
  (*p)++;
}
