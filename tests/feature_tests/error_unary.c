int main() {
  // error: unary minus requires arithmetic type operand
  -"";

  // error: unary plus requires arithmetic type operand
  +"";

  // error: bit-complement requires integral type operand
  ~"";
}
