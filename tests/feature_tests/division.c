int main() {
  int a = 5, b = 10;

  int c = b / a;
  int d = b / c;
  int e = b / d;
  int f = e / 2;
  int g = f / 2;

  if(g != 0) return 1;

  int h = 30, i = 3, j = 5;

  int k = h / i / j;
  if(k != 2) return 2;

  int l = k / k;
  if(l != 1) return 3;

  int m = 3;
  m = m / m;
  if(m != 1) return 4;

  unsigned long n = 4294967295;
  int o = -4;
  if(n / o != (unsigned long)4294967295 / -4) return 5;
}
