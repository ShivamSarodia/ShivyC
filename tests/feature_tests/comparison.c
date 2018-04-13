int main() {
  int a = 5, b = 10; long c; unsigned int d;

  if(a == b) return 1;

  if(5 == a);
  else return 36;

  if(&a == &b) return 2;

  if(&a != &a) return 3;

  if(&a == 0) return 4;

  if(&a == (0)) return 5;

  if(0 == &a) return 6;

  void* v = &a;
  if(v == 0) return 10;
  if(0 == v) return 11;
  if(v == &b) return 12;
  if(&b == v) return 13;
  if(v != &a) return 14;

  // Test imm64 operands
  long e = 17179869184;
  if(e != 17179869184) return 15;
  if(17179869184 != e) return 16;

  ////////////////////////////////////

  a = 5; b = 10;
  if(a > b) return 17;
  if(a >= b) return 18;
  if(b < a) return 19;
  if(b <= a) return 20;
  if(a < 5) return 21;
  if(b < 10) return 22;

  unsigned short f; unsigned int g;
  f = 65535;
  g = 4294967295;

  if(f > g) return 25;
  if(f >= g) return 26;
  if(g < f) return 27;
  if(g <= f) return 28;
  if(f < 5) return 29;
  if(g < 5) return 30;

  // Test imm64 operands
  e = 17179869184;
  if(17179869184 < 17179869184) return 31;
  if(17179869184 < 17179869183) return 32;
  if(e < 17179869183) return 33;

  int array[5];
  if(&array[1] > &array[3]) return 21;
  if(&array[1] >= &array[3]) return 22;
  if(&array[3] < &array[1]) return 23;
  if(&array[3] <= &array[1]) return 24;

  // Test order of ops between < and ==
  if(3 < 4 == 9 < 3) return 34;
  if(3 < 4 != 5 < 6) return 35;

  return 0;
}
