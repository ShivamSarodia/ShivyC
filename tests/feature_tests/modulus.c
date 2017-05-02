int main() {
  if(20 % 3 != 2) return 1;
  if(3 % 3 != 0) return 2;

  int a = 5, b = 13;
  if(a % b != 5) return 3;
  if(b % a != 3) return 4;

  long l = 3;
  if(a % l != 2) return 5;
  if(a % 1099511627776 != a) return 6;
  if(1099511627776 % a != 1) return 7;
  if(1099511627776 % 1099511627776 != 0) return 8;
}
