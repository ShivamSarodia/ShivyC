int array1[];
int array2[];
int array3[][5];
int array4[5][5];

// verify typedef doesn't get completed
typedef int T[];
T e;
int e[10];
T f;
int f[5];

struct S s;

int check_completed(void);

int main() {
  // verify these are compatible types
  // (complete and incomplete arrays are compatible)
  &array1 == &array2;

  // complete array1
  extern int array1[5];
  &array1 == &array2;

  // (complete and incomplete are compatible)
  &array3 == &array4;

  // todo: test sizeof(S)
  return check_completed();
}

// complete arrays
int array2[5];
int array3[5][5];

struct S {
  int a, b;
} s;

int check_completed() {
  s.a = 3;
  s.b = 5;
  if(s.a != 3) return 1;
  if(s.b != 5) return 2;

  &array1 == &array2;
  &array3 == &array4;

  return 0;
}
