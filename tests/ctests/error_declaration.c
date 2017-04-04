int main() {
  // Issue: 3: error: variable of void type declared
  void a;

  // Issue: 6: error: missing identifier name in declaration
  int *;

  // Issue: 9: error: two or more data types in declaration specifiers
  int long a;

  // Issue: 12: error: both signed and unsigned in declaration specifiers
  unsigned signed int a;
}
