int main() {
  int a = 14;

  if (a>>1 != 7) return 1;
  if (a>>2 != 3) return 2;
  if (a<<1 != 28) return 3;
  if (a<<2 != 56) return 4;

  int b = 3;
  if (a>>b != 1) return 5;
  if (a<<b != 112) return 6;

  int c = a>>(b-1);
  if (c != 3) return 7;

  if ((1<<16)-1 != 65535) return 8;
  if (3<<8 != 768) return 9;
}
