int main() {
  int a = 5, b = 10; long c; unsigned int d;

  // error: comparison between incomparable types
  &a == 1;

  // error: comparison between distinct pointer types
  &a == &c;

  // error: comparison between distinct pointer types
  &a == &d;

  // error: comparison between distinct pointer types
  &a < &d;

  // error: comparison between incomparable types
  &a < 1;
}
