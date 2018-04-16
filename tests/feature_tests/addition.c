int main() {
  int a = 5, b = 10;

  int c = a + b;
  if(c != 15) return 1;

  int d = c + 5;
  if(d != 20) return 2;

  int e = 2 + 4;
  if(e != 6) return 3;

  int f = e + d;
  if(f != 26) return 4;

  int g = f + f + e;
  if(g != 58) return 5;

  int i = g + g;
  i = i + i;

  if(i != 232) return 6;

  // Test imm64 cases

  // used to modify variable liveliness
  int dummy;
  dummy = 0;

  // this variable is always live
  long never_dead;
  never_dead = 1099511627776;

  long j = 1099511627776;
  never_dead = j + 1099511627776;
  if(never_dead != 1099511627776 + 1099511627776) return 7;

  long k = 1099511627776;
  never_dead = 1099511627776 + k;
  if(never_dead != 1099511627776 + 1099511627776) return 8;

  long not_dead = 1099511627776;
  never_dead = not_dead + 1099511627776;
  if(never_dead != 1099511627776 + 1099511627776) return 9;

  never_dead = 1099511627776 + not_dead;
  if(never_dead != 1099511627776 + 1099511627776) return 10;
  if(1099511627776 + 1099511627776 != never_dead) return 11;

  dummy = dummy + never_dead + not_dead;

  unsigned int l = 4294967295;
  unsigned int m = 4294967295;
  if(l + m != (unsigned int)4294967295 + (unsigned int)4294967295) return 12;
}
