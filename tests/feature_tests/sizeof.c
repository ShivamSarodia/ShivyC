#include <stdio.h>

int main() {

  struct A {
    int a_int_one;
    struct B {
      int b_int_one;
      long b_long;
      int b_int_two;
    } b_struct;
    int a_int_two, *a_ptr;
    int;
  } a;

  struct A q;
  q.a_int_one = 4;

  printf("here is the size : %i", sizeof(q.a_int_one));

}