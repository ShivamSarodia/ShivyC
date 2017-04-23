int main() {
  // error: use of undeclared identifier 'a'
  a = 0;
  // error: use of undeclared identifier 'a'
  a;

  int a; int b; int c;
  a = 0;
  // error: use of undeclared identifier 'd'
  d = 0;
  // error: use of undeclared identifier 'd'
  a = d;
  // error: use of undeclared identifier 'd'
  a = d + d;

  {
    int e;
    e;
  }

  // error: use of undeclared identifier 'e'
  e;
}
