 int main() {
  int a; int b;

  // error: operand of unary '&' must be lvalue
  &(a + b);

  // error: operand of unary '*' must have pointer type
  *a;

  // error: invalid conversion between types
  a = &b;

  int* c;
  // error: invalid conversion between types
  c = 10;

  // error: operand of unary '*' must have pointer type
  *a = 1;

  void* p;
  // error: expression on left of '=' is not assignable
  *p = 1;

  int *f; unsigned int *g;
  // error: conversion from incompatible pointer type
  f = g;

  int (*h)();
  // error: conversion from incompatible pointer type
  h = f;

  return 0;
 }
