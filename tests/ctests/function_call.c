int isalpha(int);
int div(int, int);

int strcmp(char*, char*);
char* strncpy(char*, char*, long);

int main() {
  // Try out a few function calls from standard library.

  _Bool b;

  b = isalpha(65); // 'A'
  if(b != 1) return 1;

  b = isalpha(52);
  if(b != 0) return 2;

  // This is super ratchet, but works for now. The div function
  // accepts two integers and returns a struct. It turns out the
  // quotient of this struct is returned in the integer return
  // register, so this test works.
  if(div(50, 5) != 10) return 3;

  char str1[5], str2[5];
  str1[0] = str2[0] = 100;
  str1[1] = str2[1] = 101;
  str1[2] = str2[2] = 102;
  str1[3] = str2[3] = 103;
  str1[4] = str2[4] = 0;
  if(strcmp(str1, str2)) return 4;

  // Issue: 33: warning: conversion from incompatible pointer type
  int* p = str1;
  // Issue: 35: warning: conversion from incompatible pointer type
  if(strcmp(p, str2)) return 13;

  str2[3] = 102;
  if(strcmp(str1, str2) != 1) return 5;

  str2[0] = 106;
  str2[1] = 107;
  str2[2] = 108;
  char* out = strncpy(str1, str2, 3);

  if(out[0] != 106) return 6;
  if(out[1] != 107) return 7;
  if(out[2] != 108) return 8;
  if(out[3] != 103) return 9;
  if(out[4] != 0) return 10;

  // Fun with function pointers!
  // Issue: 53: warning: conversion from incompatible pointer type
  void* f1 = isalpha;
  // Issue: 55: warning: conversion from incompatible pointer type
  if(f1 != isalpha) return 11;

  int (*f2)(int) = isalpha;
  if(f2(5)) return 12;

  // Test function pointer casting

  // Issue: 63: warning: conversion from incompatible pointer type
  int* p1 = isalpha;
  // Issue: 65: warning: conversion from incompatible pointer type
  int (*f3)(int, int) = isalpha;
  // Issue: 67: warning: conversion from incompatible pointer type
  int (*f4)(int*) = isalpha;
  // Issue: 69: warning: conversion from incompatible pointer type
  int* (*f5)(int) = isalpha;


  return 0;
}
