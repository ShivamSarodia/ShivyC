int main() {
  typedef int a;
  // error: 'a' redeclared as incompatible type in same scope
  typedef long a;

  struct {
    // error: cannot have storage specifier on struct member
    typedef int a;
  };

  typedef struct S {
    int a;
    int b;
  } struct_S;

  typedef struct {
    int a;
    int b;
  // error: 'struct_S' redeclared as incompatible type in same scope
  } struct_S;

  const struct_S s;
  // error: expression on left of '=' is not assignable
  s.a = 3;

  typedef int A;
  {
    // error: too many storage classes in declaration specifiers
    static extern int A;
    // error: use of undeclared identifier 'A'
    A = 3;
  }

  int B;
  {
    // error: too many storage classes in declaration specifiers
    static typedef int B;
    // error: use of undeclared type definition 'B'
    B b;
  }
}

typedef int F(void);
// error: function definition missing parameter list
F f { }

// error: function definition cannot be a typedef
typedef int function(int a) {
  return 0;
}

// error: storage class specified for function parameter
int function(typedef int a) {
  return 0;
}
