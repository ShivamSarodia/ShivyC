int main() {
  struct S1 {
    int x;
  }* a;

  struct S2 {
    long y;
  }* b;

  // error: conversion from incompatible pointer type
  a = (struct S2*) b;

  // error: can only cast to scalar or void type
  (struct S1) 4;

  // error: can only cast from scalar type
  (int) *a;

  // error: expected abstract declarator, but identifier name was provided
  (int x) a;

  // error: storage specifier not permitted here
  (static int) a;
}
