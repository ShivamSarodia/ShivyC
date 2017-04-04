// Tests dereference operator on left-side of assignment.

int main() {
  int a = 1;
  int* p1 = &a;

  *p1 = 2;
  if(a != 2) return 1;

  int b = 0;
  *(&b) = 3;
  if(b != 3) return 2;

  int c;
  int* p2; int* p3;
  p2 = &c + 2;
  *p2 = 4;
  p3 = &c + 2;
  if(*p2 != *p3) return 3;

  char d = 4;
  long e = 3;
  *(&d) = e;
  if(d != 3) return 4;

  d = 4;
  *(&e) = d;
  if(e != 4) return 5;

  // dereferencing pointer stored on stack
  int* p4; int f;
  &p2;
  p2 = &f;
  *p2 = 10;
  if(f != 10) return 6;

  return 0;
}
