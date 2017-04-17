extern void* stdout;
extern int does_not_exist;

int main() {
  auto char* p;
  p = stdout;
  if(*p + 124 != 0) return 1;

  extern int inside_main_function;

  return 0;
}
