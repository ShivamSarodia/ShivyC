int main() {
  int a;

  // error: redefinition of 'a'
  int a;

  {
    int a;  // OK
  }

  // error: redefinition of 'a'
  int a;
}
