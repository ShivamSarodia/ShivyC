int main() {
  int a; int b; long c; unsigned int d;

  a = 5; b = 10;
  if(a == b) return 1;

  if(&a == &b) return 2;

  if(&a != &a) return 3;

  if(&a == 0) return 4;

  if(&a == (0)) return 5;

  if(0 == &a) return 6;

  // Issue: 18: warning: comparison between incomparable types
  if(&a == 1) return 7;

  // Issue: 21: warning: comparison between distinct pointer types
  if(&a == &c) return 8;

  // Issue: 24: warning: comparison between distinct pointer types
  if(&a == &d) return 9;

  void* v;
  v = &a;
  if(v == 0) return 10;
  if(0 == v) return 11;
  if(v == &b) return 12;
  if(&b == v) return 13;
  if(v != &a) return 14;

  return 0;
}
