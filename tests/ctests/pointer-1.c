// For testing dereference operator on left-side of assignment, see pointer-2.c

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

  // Verify reference operator reverses dereference pointer
  c = &a;
  if(&(*c) != &a) return 5;

  // Assignment of non-void to void
  void* v;
  v = &a;

  // Assignment of void to non-void
  int* e;
  e = v;

  // Assignment of null pointer constant
  v = 0;
  e = 0;

  // Issue: 35: warning: assignment from incompatible pointer type
  int *f; unsigned int *g;
  f = g;

  _Bool h;
  h = &a; // Value is checked at very end of this main() function

  // Address-of operator where output is on the stack
  int* i_on_stack; int j;
  &i_on_stack;
  i_on_stack = &j;
  if(i_on_stack != &j) return 3;

  // Read-at where address is on stack
  j = 10;
  i_on_stack = &j;
  j = *i_on_stack;
  if(j != 10) return 4;

  if(h) return 0;
  return 1;
}
