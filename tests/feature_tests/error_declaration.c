int main() {
  // error: variable of void type declared
  void a;

  // error: missing identifier name in declaration
  int *;

  // error: two or more data types in declaration specifiers
  int long a;

  // error: both signed and unsigned in declaration specifiers
  unsigned signed int a;

  // error: extern variable has initializer
  extern int a = 10;

  // error: two or more storage classes in declaration specifiers
  extern auto int b;
}
