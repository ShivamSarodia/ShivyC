#include <stdio.h>

int main() {
  struct S1 {
    int x;
  } a, *p1 = &a;

  struct S2 {
    long y;
  } b, *p2 = &b;

  p1 = (struct S1*) p2;
  p2->y = 75;
  if(p1->x != 75) return 1;

  unsigned int c, d;
  d = 65536;
  c = (unsigned char) d;
  if(c != 0) return 2;

  unsigned char e = -10;
  int f = (signed char) e;
  if(f != -10) return 3;

  (void) 5;
}
