int main() {
  struct A {} a;

  // error: '&&' operator requires scalar operands
  a && a;

  // error: '||' operator requires scalar operands
  1 || a;

  // error: '||' operator requires scalar operands
  a || 1;

  // error: '!' operator requires scalar operand
  !a;
}
