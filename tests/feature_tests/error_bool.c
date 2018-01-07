int main() {
  struct A {} a;

  // error: '&&' operator requires scalar operands
  a && a;

  // error: '||' operator requires scalar operands
  a || a;

  // error: '!' operator requires scalar operand
  !a;
}
