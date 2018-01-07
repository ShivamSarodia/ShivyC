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
}
