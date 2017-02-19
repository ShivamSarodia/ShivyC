int main() {
  int a; int b; int c; int d; int e;
  a = 5; b = 10; c = 2;
  c = b + a * b + 10 * a / c + 10 * 3 / 3;
  d = c * b + a / 2;
  e = d * c;

  if(e != 90440) return 1;
}
