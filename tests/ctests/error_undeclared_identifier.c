int main() {
  // Issue: 3: error: use of undeclared identifier 'a'
  a = 0;
  // Issue: 5: error: use of undeclared identifier 'a'
  a;

  int a; int b; int c;
  a = 0;
  // Issue: 10: error: use of undeclared identifier 'd'
  d = 0;
  // Issue: 12: error: use of undeclared identifier 'd'
  a = d;
  // Issue: 14: error: use of undeclared identifier 'd'
  a = d + d;
}
