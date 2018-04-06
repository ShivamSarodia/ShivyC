// Verify we can declare variables before and after main
extern int a;

int f0(int[5], int());

int f1(void);

int f2();

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

  // verify f3 and f4 are compatible
  int (*f3)(int, int, int), f4(int, int, int);
  // TODO: uncomment this when function definition is supported.
  // Today, this line produces a linker error becuase f4 is not
  // defined anywhere.
  // f3 = f4;
}

extern int z;
