int strcmp(char*, char*);

int main() {
  if(strcmp("hello", "hello")) return 1;

  char (*a)[6] = &"hello";
  if(strcmp("hello", *a)) return 2;

  return 0;
}
