#include <stdio.h>

int main() {

  if (sizeof(_Bool) != 1) return 1;
  if (sizeof(char) != 1) return 2;
  if (sizeof(char signed) != 1) return 3;
  if (sizeof(char unsigned) != 1) return 4;;
  if (sizeof(short) != 2) return 5;
  if (sizeof(short signed) != 2) return 6;
  if (sizeof(int short) != 2) return 7;
  if (sizeof(int short signed) != 2) return 8;
  if (sizeof(short unsigned) != 2) return 9;
  if (sizeof(int short unsigned) != 2) return 10;
  if (sizeof(int) != 4) return 11;
  if (sizeof(signed) != 4) return 12;
  if (sizeof(int signed) != 4) return 13;
  if (sizeof(unsigned) != 4) return 14;
  if (sizeof(int unsigned) != 4) return 15;
  if (sizeof(long) != 8) return 16;
  if (sizeof(long signed) != 8) return 17;
  if (sizeof(int long) != 8) return 18;
  if (sizeof(int long signed) != 8) return 19;
  if (sizeof(long unsigned) != 8) return 20;
  if (sizeof(int long unsigned) != 8) return 21;
  if (sizeof(int *) != 8) return 22;

  int a = 1;
  if (sizeof a != 4) return 23;

  if (sizeof 32 != 4) return 24;

  int b[3];
  if (sizeof b != 12) return 24;

  struct C {
    int a_int_one;
    struct B {
      int b_int_one;
      long b_long;
      int b_int_two;
    } b_struct;
    int a_int_two, *a_ptr;
  } c;
  struct C q;
  if (sizeof q != 32) return 26;
  if (sizeof q.a_int_one != 4) return 27;
  if (sizeof q.b_struct != 16) return 28;

  return 0;
}