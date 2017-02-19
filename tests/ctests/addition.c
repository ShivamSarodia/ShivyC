int main() {
  int a; int b;
  a = 5; b = 10;

  int c;
  c = a + b;
  if(c != 15) return 1;

  int d;
  d = c + 5;
  if(d != 20) return 2;

  int e;
  e = 2 + 4;
  if(e != 6) return 3;

  int f;
  f = e + d;
  if(f != 26) return 4;

  int g;
  g = f + f + e;
  if(g != 58) return 5;

  int i;
  i = g + g;
  i = i + i;

  if(i != 232) return 6;
}
