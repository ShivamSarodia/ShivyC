int main() {
  union R {
    // error: cannot have storage specifier on union member
    extern int a;

    // error: cannot have storage specifier on union member
    auto int a;

    // error: cannot have incomplete type as union member
    union R a;

    // error: cannot have function type as union member
    int function(int);

    // error: missing name of union member
    int*;
  };

  union S {
    int apple;
    // error: duplicate member 'apple'
    int apple;
    // error: duplicate member 'apple'
    int apple;
    // error: duplicate member 'banana'
    int banana, banana;
  };

  union A {
    int a;
  } *a;

  union B {
    int a;
  } *b;

  // error: conversion from incompatible pointer type
  a = b;

  union C *p;
  // error: invalid arithmetic on pointer to incomplete type
  p + 1;

  union C {
    int a;
  };
  p + 1;

  {
    union C* q;
    q + 1;

    union C;
    union C* r;

    // error: invalid arithmetic on pointer to incomplete type
    r + 1;

    union C {
      int a;
    };

    r + 1;
  }

  union D {
    int a;
  };

  // error: redefinition of 'union D'
  union D {
    int a;
  };

  // error: defined as wrong kind of tag 'struct D'
  struct D {
    int b;
  };

  union D1;

  // error: defined as wrong kind of tag 'struct D1'
  struct D1;

  union D2 {
    int a;
  };

  // error: defined as wrong kind of tag 'struct D2'
  struct D2 ddd;

  union Union {
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
