int main() {
  signed a; int b; int c; int d; int e; int f; int g; int h;
  a = b = 10;
  c = a;
  d = b;
  (e) = c;
  ((f)) = d;
  g = 20;

  // Force variables to be on stack
  int i; int j; char k;
  &i; &j;
  i = g;
  j = i;
  j = k;


  if(a != 10) return 1;
  if(b != 10) return 2;
  if(c != 10) return 3;
  if(d != 10) return 4;
  if(e != 10) return 5;
  if(f != 10) return 6;
  if(g != 20) return 7;
}
