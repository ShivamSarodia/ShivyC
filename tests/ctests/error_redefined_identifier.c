int main() {
  int a;

  // Issue: 5: error: redefinition of 'a'
  int a;

  {
    int a;  // OK
  }

  // Issue: 12: error: redefinition of 'a'
  int a;
}
