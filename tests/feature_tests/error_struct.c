int main() {
  struct R {
    // error: cannot have storage specifier on struct member
    extern int a;

    // error: cannot have storage specifier on struct member
    auto int a;

    // error: cannot have incomplete type as struct member
    struct R a;

    // error: cannot have function type as struct member
    int function(int);

    // error: missing name of struct member
    int*;
  };

  struct S {
    int apple;
    // error: duplicate member 'apple'
    int apple;
    // error: duplicate member 'apple'
    int apple;
    // error: duplicate member 'banana'
    int banana, banana;
  };

  struct A {
    int a;
  } *a;

  struct B {
    int a;
  } *b;

  // warning: conversion from incompatible pointer type
  a = b;

  struct C *p;
  // error: invalid arithmetic on pointer to incomplete type
  p + 1;

  struct C {
    int a;
  };
  p + 1;

  {
    struct C* q;
    q + 1;

    struct C;
    struct C* r;

    // error: invalid arithmetic on pointer to incomplete type
    r + 1;

    struct C {
      int a;
    };

    r + 1;
  }

  struct D {
    int a;
  };

  // error: redefinition of 'struct D'
  struct D {
    int a;
  };

  struct Struct {
    int a;
    long b;
    int* c;
  } s, *s_p;

  // error: request for member in something not a structure or union
  10.a;

  // error: request for member in something not a structure or union
  s_p.a;

  int *int_ptr;
  // error: request for member in something not a structure or union
  int_ptr->a;

  // error: first argument of '->' must have pointer type
  s->a;

  // error: structure or union has no member 'd'
  s.d;
}
