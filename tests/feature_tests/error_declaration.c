// error: storage class specified for function parameter
int func(auto int a);

// error: 'void' must be the only parameter
int func1(void, void);

typedef int Function(void);
typedef int Array[10];

// error: function cannot return function type
Function f(void);
// error: function cannot return array type
Array f(void);

extern int var;
// error: redeclared 'var' with different linkage
static int var;
// error: redeclared 'var' with incompatible type
extern long var;

int var1;
// error: redeclared 'var1' with different linkage
static int var1;

int main() {
  // error: variable of incomplete type declared
  void a;

  // error: missing identifier name in declaration
  int *;

  // error: unrecognized set of type specifiers
  int int a;

  // error: unrecognized set of type specifiers
  unsigned signed int a;

  // error: local variable with linkage has initializer
  extern int a = 10;

  // error: too many storage classes in declaration specifiers
  extern auto int b;

  {
    int c;
  }
  // error: use of undeclared identifier 'c'
  c;

  int (*f1)(int), f2(int, int);
  // error: conversion from incompatible pointer type
  f1 = f2;

  void (*f3)(int);
  // error: conversion from incompatible pointer type
  f1 = f3;

  void (*f4)(long);
  // error: conversion from incompatible pointer type
  f3 = f4;

  int redefined;
  // error: redefinition of 'redefined'
  int redefined;
}
