int main() {
  int a;
  a = 10;
  if(*(&a) != 10) return 1;

  long b;
  b = 20;
  if(*(&b) + 50 != 70) return 2;

  // Assignment of compatible pointer types
  int* c; int *d;
  c = &a;
  c = d;

  // Assignment of non-void to void
  void* v;
  v = &a;

  // Assignment of void to non-void
  int* e;
  e = v;

  // Assignment of null pointer constant
  v = 0;
  e = 0;

  // Issue: 29: warning: assignment from incompatible pointer type
  int *f; unsigned int *g;
  f = g;

  _Bool h;
  h = &a;

  if(h) return 0;
  return 1;
}
