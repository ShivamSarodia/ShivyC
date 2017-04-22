int main() {
  // These tests are pretty finicky, as they reply on these variables being
  // declared on the stack with a particular order/alignment.

  int a = 5, b = 10, c = 15;

  // This line forces the register allocator to declare a, b, and c on the stack
  // in the desired order.
  &a; &b; &c;

  if(*(&c + 1) != 10) return 1;
  if(*(1 + &c) != 10) return 2;
  if(*(&c + 2) != 5) return 3;
  if(*(2 + &c) != 5) return 4;
  if(*(&b + 1) != 5) return 5;
  if(*(1 + &b) != 5) return 6;
  if(&b + 1 != &a) return 7;
  if(1 + &b != &a) return 8;

  if(&a - &b != 1) return 9;
  if(&a - &c != 2) return 10;
  if(&a - 1 != &b) return 11;
  if(&a - 2 != &c) return 12;

  return 0;
}
