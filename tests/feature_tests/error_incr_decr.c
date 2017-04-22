int main() {
  // Issue: 3: error: operand of increment operator not a modifiable lvalue
  4--;

  int array[5];
  // Issue: 7: error: operand of increment operator not a modifiable lvalue
  array--;
}
