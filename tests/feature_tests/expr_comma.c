int main() {
  int a = (3, 5);
  int *p = (10, &a);

  if(a != 5) return 1;
  if(p != &a) return 2;
}
