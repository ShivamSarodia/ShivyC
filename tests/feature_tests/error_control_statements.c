int main() {
  // error: expression on left of '=' is not assignable
  if(3 = 5) {
    return 1;
  }

  // error: use of undeclared identifier 'a'
  if(a = 5) {
    return 2;
  }

  // error: expression on left of '=' is not assignable
  while(3 = 5) {
    return 3;
  }

  // error: use of undeclared identifier 'a'
  while(a = 5) {
    return 4;
  }

  return 0;
}
