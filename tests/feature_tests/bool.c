int main() {
  if((3 && 4) != 1) return 1;
  if((0 && 4) != 0) return 2;
  if(0 && 4) return 3;
  if((3 && 0) != 0) return 4;
  if(3 && 0) return 5;

  int a, *p = &a;
  if((p && 0) != 0) return 6;
  if(p && 0) return 7;
  if((p && p) != 1) return 8;

  if((3 || 4) != 1) return 9;
  if((0 || 4) != 1) return 10;
  if((2 || 0) != 1) return 11;
  if((0 || 0) != 0) return 12;
  if(0 || 0) return 13;

  if((0 || 0) != 0) return 12;
  if((p || 0) != 1) return 14;
  if((p || p) != 1) return 15;

  if(!p != 0) return 16;
  if(!p) return 16;
  if(!0 != 1) return 17;

  int n = 0;
  0 && (n = 1);
  if(n == 1) return 18;

  (n = 1) && 0;
  if(n != 1) return 19;

  1 || (n = 3);
  if(n == 3) return 20;

  (n = 3) || 1;
  if(n != 3) return 21;
}
