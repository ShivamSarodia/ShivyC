int main() {
  int a; int b;
  a = 2; b = 3;

  int c;
  c = a * b;

  int d;
  d = c * 5;

  int e;
  e = 2 * 4;

  int f;
  f = c * d * e;
  f = f * f;

  if(f != 2073600) return 1;
  return 0;
}
