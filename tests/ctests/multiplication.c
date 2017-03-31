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

  unsigned int g;
  unsigned int h;
  unsigned int i;
  g = 5;
  h = g * 10; // 50
  h = 10 * g; // 50
  i = g * h; // 250

  if(i != 250) return 2;

  if(i / g != h) return 3;

  return 0;
}
