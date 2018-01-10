// For testing dereference operator on left-side of assignment, see pointer-2.c

int main() {
  int a = 10;
  if(*(&a) != 10) return 1;

  long b = 20;
  if(*(&b) + 50 != 70) return 2;

  // Assignment of compatible pointer types
  int* c = &a; int *d;
  c = &a;
  c = d;

  // Verify reference operator reverses dereference pointer
  c = &a;
  if(&(*c) != &a) return 5;

  // Assignment of non-void to void
  void* v = &a;

  // Dereference void pointer
  *v;

  // Assignment of non-void double pointer to void
  int *q = &a;
  v = &q;

  // Assignment of void to non-void
  int* e = v;

  // Assignment of null pointer constant
  v = 0;
  e = 0;

  // Value of below is checked at very end of this main() function
  _Bool h = &a;

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
