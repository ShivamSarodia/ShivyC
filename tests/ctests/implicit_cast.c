int main() {
  _Bool b;

  char c;
  unsigned char uc;

  short s;
  unsigned short us;
  unsigned short us_2;

  int i;
  unsigned int ui;

  long l;
  unsigned long ul;

  // Until negative literals are supported, this is how we insert -1.
  int neg_one = 4294967295;

  c = neg_one;
  if(c != neg_one) return 1;

  s = neg_one;
  if(s != neg_one) return 2;
  if(s == 65535) return 3;

  us = neg_one;
  if(us == neg_one) return 4;
  if(us != 65535)  return 5;

  s = neg_one;
  us_2 = s;
  if(us != 65535)  return 6;
  if(us != us_2)  return 7;

  ui = neg_one;
  if(ui != 4294967295) return 8;

  s = neg_one;
  ui = s;
  if(ui != 4294967295) return 9;

  us = neg_one;
  ui = us;
  if(ui != 65535) return 9;

  s = neg_one;
  ui = s;
  i = ui;  // Technically undefined behavior, per the spec.
  if(i != neg_one) return 10;

  c = neg_one;
  l = c;
  if(l + 1 != 0) return 11;

  s = neg_one;
  l = s;
  if(l + 1 != 0) return 12;

  l = neg_one;
  if(l + 1 != 0) return 13;

  // Test integer promotion
  char c1 = 30, c2 = 40, c3 = 10, c4;
  c4 = (c1 * c2) / c3;
  if(c4 != 120) return 14;

  unsigned short us1 = 30, us2 = 40, us3 = 10, us4;
  us1 = 30; us2 = 40; us3 = 10;
  us4 = (us1 * us2) / us3;
  if(us4 != 120) return 15;

  // Test integer conversion
  long l1 = 1073741824, i1;
  // Because large immediate values are not yet supported, we split up
  // l1 in this way. l1 = 2^32.
  l1 = l1 + l1 + l1 + l1;
  if(l1 * 2 / 8 != 1073741824) return 16;

  // Test unsigned integer conversion
  int i2; unsigned int ui2;
  i2 = 2*neg_one;
  ui2 = 1;
  if(i2 + ui2 != 4294967295) return 17;

  // Test int/long conversion.
  long l2; int i3;
  l2 = 2147483644; // 2^31-4
  i3 = 4;
  if(i3 * l2 / i3 != 2147483644) return 18;

  // Test signed/unsigned conversion when signed is bigger
  long l3 = 100; unsigned int i4 = 100;
  if(l3 != i4) {
    return 20;
  }
  if(i4 != l3) {
    return 21;
  }

  b = 0;
  if(b) return 19;

  b = 10;
  if(b) {
    b = i3;
    if(b) {
      return 0;
    }
  }
  return 1;
}
