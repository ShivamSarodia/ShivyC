int main() {
  typedef int a;
  typedef int a;

  typedef struct S struct_S;
  typedef struct S {
    int a;
    int b;
  } struct_S;

  typedef struct S struct_S1;
  // verify a struct is compatible with itself
  struct_S *s;
  struct_S1 *s1;
  s = s1;

  typedef int A;
  {
    A A;
    A = 3;
    if(A != 3) return 1;
  }

  typedef A* B, C;
  C c;
  B b = &c;
  c = 3;
  if(*b != 3) return 2;
}

typedef int a;
int function(a b, int a) {
  return a;
}
