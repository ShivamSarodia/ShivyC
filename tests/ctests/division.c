int main() {
  int a; int b;
  a = 5; b = 10;

  int c;
  c = b / a;

  int d;
  d = b / c;

  int e;
  e = b / d;

  int f;
  f = e / 2;

  int g;
  g = f / 2;
  if(g != 0) return 1;

  int h; int i; int j;
  h = 30; i = 3; j = 5;

  int k;
  k = h / i / j;
  if(k != 2) return 2;

  int l;
  l = k / k;
  if(l != 1) return 3;

  int m;
  m = 3;
  m = m / m;
  if(m != 1) return 4;
}
