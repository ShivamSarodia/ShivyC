// Verify we can declare variables before and after main
extern int a;

int f0(int[5], int());

int f1(void);

int f2();

int f4(int a, int b, int c) { return 0; }

int func(int a, int b) {
  a; b;
  return a;
}

// Test declaration of function returning function.
int (*getFunc(int z))(int a, int b) {
  z;
  return func;
}

int main() {
  int;

  int b = 3 + 4;

  int arr[3], (*c)[3] = &arr, *d[3], e = 2;
  (*c)[e];

  d[e] = &b;
  *d[e];

  int *f(int, unsigned int* b, long *[5], long (*)[5]);
  int g();
  int h(void);
  int *i();
  int *j(int);
  int *k(int(int));

  // verify pointer to function and decayed function are compatible
  int (*f3)(int, int, int);
  f3 = f4;
}

extern int z;
