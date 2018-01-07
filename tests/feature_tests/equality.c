int main() {
  int a = 5, b = 10; long c; unsigned int d;

  a = 5; b = 10;
  if(a == b) return 1;

  if(&a == &b) return 2;

  if(&a != &a) return 3;

  if(&a == 0) return 4;

  if(&a == (0)) return 5;

  if(0 == &a) return 6;

  // error: comparison between incomparable types
  if(&a == 1) return 7;

  // warning: comparison between distinct pointer types
  if(&a == &c) return 8;

  // warning: comparison between distinct pointer types
  if(&a == &d) return 9;

  void* v = &a;
  if(v == 0) return 10;
  if(0 == v) return 11;
  if(v == &b) return 12;
  if(&b == v) return 13;
  if(v != &a) return 14;

  // Test imm64 operands
  long e = 17179869184;
  if(e != 17179869184) return 15;
  if(17179869184 != e) return 16;

  return 0;
}
