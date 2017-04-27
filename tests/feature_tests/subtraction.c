int main() {
  int a = 10, b = 5;
  if(a - b != 5) return 1;

  int c = a - b;
  if(c != 5) return 2;

  int d = a - 5;
  if(d != 5) return 3;

  // Test associativity of subtraction
  if(3 - 4 - 5 == 3 - (4 - 5)) return 4;
  if(3 - 4 - 5 != (3 - 4) - 5) return 5;

  // Test imm64 cases

  // used to modify variable liveliness
  int dummy;
  dummy = 0;

  // this variable is always live
  long never_dead;
  never_dead = 1099511627776;

  long j = 1099511627776;
  never_dead = j - 1099511627776;
  if(never_dead != 1099511627776 - 1099511627776) return 7;

  long k = 1099511627776;
  never_dead = 1099511627776 - k;
  if(never_dead != 1099511627776 - 1099511627776) return 8;

  long not_dead = 1099511627776;
  never_dead = not_dead - 1099511627776;
  if(never_dead != 1099511627776 - 1099511627776) return 9;

  never_dead = 1099511627776 - not_dead;
  if(never_dead != 1099511627776 - 1099511627776) return 10;
  if(1099511627776 - 1099511627776 != never_dead) return 11;

  dummy = dummy - never_dead - not_dead;
}
