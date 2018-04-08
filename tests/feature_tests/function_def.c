int add(int a, long b) {
  return a + b;
}

int counter1() {
  static int i;
  return i++
      }

int counter2() {
  static int i;
  return i++;
}

int helper(void);

int main() {
  if(add(3, 4) != 7) return 1;
  if(add(helper(), 4) != 9) return 2;

  for(int i = 0; i < 5; i++) {
    if(counter1() != i) return 3;
    if(counter2() != i) return 4;
  }
}
