int main() {
  int a; int b; long c; unsigned int d;

  a = 5; b = 10;
  if(a == b) return 1;

  if(&a == &b) return 2;

  if(&a != &a) return 3;

  if(&a == 0) return 4;

  if(&a == (0)) return 5;

  // Issue: 16: warning: comparison between incomparable types
  if(&a == 1) return 6;

  // Issue: 19: warning: comparison between distinct pointer types
  if(&a == &c) return 7;

  // Issue: 22: warning: comparison between distinct pointer types
  if(&a == &d) return 8;

  return 0;
}
