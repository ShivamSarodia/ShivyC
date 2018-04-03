// Verify we can declare variables before and after main
extern int a;

int f(int[5], int());

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
}

extern int z;
