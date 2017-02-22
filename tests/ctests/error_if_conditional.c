int main() {
  // Issue: 3: error: expression on left of '=' is not assignable
  if(3 = 5) {
    return 1;
  }

  // Issue: 8: error: use of undeclared identifier 'a'
  if(a = 5) {
    return 2;
  }

  return 3;
}
