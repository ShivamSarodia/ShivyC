// Tests dereference operator on left-side of assignment.

int main() {
  int* p1;
  int a;
  a = 1;

  p1 = &a;
  *p1 = 2;
  if(a != 2) return 1;

  int b;
  *(&b) = 3;
  if(b != 3) return 2;

  int c;
  int* p2; int* p3;
  p2 = &c + 2;
  *p2 = 4;
  p3 = &c + 2;
  if(*p2 != *p3) return 3;

  char d;
  long e;
  e = 3;
  d = 4;
  *(&d) = e;
  if(d != 3) return 4;

  d = 4;
  *(&e) = d;
  if(e != 4) return 5;

  return 0;
}
