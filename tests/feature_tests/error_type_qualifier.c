int main() {
  const int a;

  // error: expression on left of '=' is not assignable
  a = 4;

  const const int* p1;
  // error: expression on left of '=' is not assignable
  *p1 = 0;
  p1 = &a;

  int *const const p2;
  *p2 = 0;
  // error: expression on left of '=' is not assignable
  p2 = &a;

  /////////////////////////////////////////////////////

  const struct A {
    int a;
    const int b;
  } X;

  // error: expression on left of '=' is not assignable
  X.a = 3;
  // error: expression on left of '=' is not assignable
  X.b = 3;
  // error: expression on left of '=' is not assignable
  *(&X.a) = 3;
  // error: expression on left of '=' is not assignable
  (&X.a)[3] = 3;

  struct A Y;
  Y.a = 3;
  // error: expression on left of '=' is not assignable
  Y.b = 3;
  // error: expression on left of '=' is not assignable
  *(&X.b) = 3;
  // error: expression on left of '=' is not assignable
  (&X.b)[3] = 3;

  // error: conversion from incompatible pointer type
  struct A* ptr_X = &X;
  struct A* ptr_Y = &Y;
}
