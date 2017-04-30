#include <stdlib.h>

int main() {
  int sum = 0;

  // This variable `a` is independent from the variable `a` used below
  int a = 10;
  for(int a = 0; a != 10; a++) {
    sum = sum + a;

    // This line does not set `a` above
    int a = 0;
  }

  if(sum != 45) return 1;

  sum = 0;
  for(a = 20; a != 80; a = a * 2) {
    sum = sum + a;
  }
  if(a != 80) return 2;
  if(sum != 60) return 3;

  sum = 0;
  for(; a != 100; ++a) {
    sum = sum + a;
  }
  if(a != 100) return 4;
  if(sum != 1790) return 5;

  sum = 0;
  for(; a != 110; ) {
    sum = sum + a;
    a++;
  }
  if(a != 110) return 6;
  if(sum != 1045) return 7;

  // Exit inside this
  int count = 0;
  for(;;) {
    count++;
    if(count == 10) exit(0);
    if(count == 0) exit(1);
  }
}
