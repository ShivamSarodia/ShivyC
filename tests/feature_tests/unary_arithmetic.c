int main() {
  int n = 5;
  unsigned char c = ' ';

  // test unary minus
  if(-n != 0-5) return 1;
  if(0-n != -5) return 2;
  if(-(n+2) != -7) return 3;
  if(-(-n) != 5) return 4;

  // test unary plus
  if(+n != 5) return 5;
  if(n != +5) return 6;
  if(+(n-2) != 3) return 7;
  if(+(-n) != -5) return 8;

  // test type promotion
  if(-c != -32) return 9;

  return 0;
}
