int main() {
  struct A *q;

  struct A {
    int a;
    struct B {
      int b;
      long c;
      int d;
    } q;
    int e, f;
  } a;

  q = &a;
  void* p1 = q + 1;
  char* p2 = p1;

  // this is a hacky test to check sizeof(struct A)
  void* p3 = p2 - 7*4;

  if(p3 != q) return 1;

  struct {};
  struct I {} b;
  if(&b != (&b + 1)) return 2;
}
