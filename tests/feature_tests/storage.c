extern int extern_var;
extern int extern_var;

extern void* stdout;

int redef_func(int, int);
int redef_func(int, int);

static int intern_var;

// should have no effect
extern int intern_var;

// has internal linkage
int extern_var_2;

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

  if(extern_var_2 != 0) return 8;
}
