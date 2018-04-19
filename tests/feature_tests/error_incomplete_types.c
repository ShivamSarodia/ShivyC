extern int a[];
extern int b[];

extern int c[];
extern int d[10];

int main() {
  extern int a[10];
  {
    // error: redeclared 'a' with incompatible type
    extern int a[12];
  }

  extern int b[10];

  // check compatibility between complete and incomplete
  &c == &d;
  extern int c[5];
  // error: comparison between distinct pointer types
  &c == &d;
}

// error: redeclared 'b' with incompatible type
extern int b[12];
