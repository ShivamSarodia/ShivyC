int main() {
  int n = 5;
  if(-n != 0-5) return 1;
  if(0-n != -5) return 2;
  if(-(n+2) != -7) return 3;
  if(-(-n) != 5) return 4;

  if(+n != 5) return 5;
  if(n != +5) return 6;
  if(+(n-2) != 3) return 7;
  if(+(-n) != -5) return 8;

  return 0;
}
