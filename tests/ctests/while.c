int main() {
  int a = 0;
  while(a != 5) a = a + 1;

  if(a != 5) return 1;

  int b = 0;
  a = 0;
  while(a != 5) {
    b = b + a;
    a = a + 1;
  }

  if(a != 5) return 2;
  if(b != 10) return 3;

  // While statement never runs
  while(b == 100) return 4;

  // While statement runs once
  int num_times_run = 0;
  while(b == 10) {
    b = b + 1;
    num_times_run = num_times_run + 1;

    if(num_times_run != 1) {
      return 5;
    }
  }

  return 0;
}
