int main() {
  int a, b;

  int* p = &a;
  int* q = p += 5;
  if(q != p) return 1;
  if(q - &a != 5) return 2;
  if(p - &a != 5) return 3;

  p = &a;
  q = p -= 5;
  if(q != p) return 4;
  if(&a - q != 5) return 5;
  if(&a - p != 5) return 6;

  a = 10;
  b = a += 5;
  if(a != b) return 7;
  if(b != 15) return 8;
  if(a != 15) return 9;

  long l = 1099511627776;  // 2^40
  a = 10;
  a += l;
  if(a != 10) return 10;

  a = 10;
  a += 1099511627776;
  if(a != 10) return 11;

  a = 10;
  b = a -= 15;
  if(a != b) return 12;
  if(a + 5 != 0) return 13;
  if(b + 5 != 0) return 14;

  a = 10;
  b = a *= 1099511627776;
  if(a != 0) return 15;
  if(b != 0) return 16;

  a = 10;
  b = a /= 2;
  if(a != 5) return 17;
  if(b != 5) return 18;

  a = 1234;
  b = a %= 100;
  if(a != 34) return 19;
  if(b != 34) return 20;
}
