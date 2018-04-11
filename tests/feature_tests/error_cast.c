int main() {
  struct S1 {
    int x;
  }* a;

  struct S2 {
    long y;
  }* b;

  // error: conversion from incompatible pointer type
  a = (struct S2*) b;


}
