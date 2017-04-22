int main() {
  int a = 5; int b = 10; int c = 2; int d; int e;
  c = b + a * b + 10 * a / c + 10 * 3 / 3;
  d = c * b + a / 2;
  e = d * c;

  if(e != 90440) return 1;
}
