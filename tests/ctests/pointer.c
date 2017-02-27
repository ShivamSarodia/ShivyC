int main() {
  int a;
  a = 10;
  if(*(&a) != 10) return 1;

  long b;
  b = 20;
  if(*(&b) + 50 != 70) return 2;

  // Issue: 11: warning: converts from pointer type without explicit cast
  a = &b;

  return 0;
}
