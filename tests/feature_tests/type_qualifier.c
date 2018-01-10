int main() {
  const int a = 4;

  const struct A {
    int a;
    int b;
  } X;

  struct B {
    const int a;
    int b;
  } Y;
  Y.b = 4;
}
