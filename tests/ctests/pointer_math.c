int main() {
  int a; int b; int c;

  // These tests are pretty finicky, as they reply on these variables being
  // declared on the stack with a particular order/alignment.
  a = 5; b = 10; c = 15;
  if(*(&c + 1) != 10) return 1;
  if(*(1 + &c) != 10) return 2;
  if(*(&c + 2) != 5) return 3;
  if(*(2 + &c) != 5) return 4;
  if(*(&b + 1) != 5) return 5;
  if(*(1 + &b) != 5) return 6;
  if(&b + 1 != &a) return 7;
  if(1 + &b != &a) return 8;

  return 0;
}
