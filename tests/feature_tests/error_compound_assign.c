int main() {
  int a, *p, *q;

  // error: expression on left of '+=' is not assignable
  10 += a;
  // error: invalid types for '+=' operator
  p += q;

  // error: expression on left of '-=' is not assignable
  10 -= a;
  // error: invalid types for '-=' operator
  p -= q;

  // error: invalid types for '*=' operator
  p *= a;
  // error: invalid types for '*=' operator
  p *= q;
  // error: expression on left of '*=' is not assignable
  10 *= a;

  // error: invalid types for '/=' operator
  p /= a;
  // error: invalid types for '/=' operator
  p /= q;
  // error: expression on left of '/=' is not assignable
  10 /= a;

  // error: invalid types for '%=' operator
  p %= a;
  // error: invalid types for '%=' operator
  p %= q;
  // error: expression on left of '%=' is not assignable
  10 %= a;

  void* v;
  // error: invalid arithmetic on pointer to incomplete type
  v += 1;
  // error: invalid arithmetic on pointer to incomplete type
  v -= 1;
}
