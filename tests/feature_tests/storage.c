extern int extern_var;
extern int extern_var;

extern void* stdout;

int redef_func(int, int);
int redef_func(int, int);

extern int a;
void set_a_to_1(void);

static int b = 7;
void set_b_to_1(void);

static int intern_var;

// should have no effect
extern int intern_var;

extern int extern_var_2;

int tent_var;
int tent_var;
int tent_var_1;
extern int tent_var_1;
void set_tent_vars(void);

int tent_var_2;
int tent_var_2 = 10;

int func();

int main() {
  auto char* p;
  p = stdout;
  if(*p + 124 != 0) return 1;

  if(extern_var != 0) return 2;
  extern_var = 18;
  if(extern_var != 18) return 3;

  {
    int extern_var;
    if(extern_var == 18) return 4;
    {
      extern int extern_var;
      if(extern_var != 18) return 5;
    }
  }

  {
    // will have internal linkage
    extern int intern_var;
    intern_var = 7;
    if(intern_var != 7) return 6;
  }
  {
    // has internal linkage also
    if(intern_var != 7) return 7;
  }

  if(extern_var_2 != 8) return 8;

  if(a != 3) return 9;
  set_a_to_1();
  if(a != 1) return 10;

  if(b != 7) return 11;
  set_b_to_1();
  if(b != 7) return 12;

  for(int i = 1; i < 10; i++) {
    if(func() != i) return 13;
  }

  if(tent_var) return 14;
  if(tent_var_1) return 15;
  set_tent_vars();
  if(tent_var != 3) return 16;
  if(tent_var_1 != 3) return 17;
  if(tent_var_2 != 10) return 18;
}

int func() {
  static int a = 1;
  return a++;
}
