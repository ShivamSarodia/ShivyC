int main() {
  int a;
  a = 10;
  if(*(&a) != 10) return 1;

  long b;
  b = 20;
  if(*(&b) + 50 != 70) return 2;

  return 0;
}
