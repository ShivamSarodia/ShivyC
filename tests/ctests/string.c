int strcmp(char*, char*);

int main() {
  if(strcmp("hello", "hello")) return 1;

  char (*a)[6] = &"hello";
  if(strcmp("hello", *a)) return 2;

  if('a' != 97) return 3;
  if('f' - 'a' != 5) return 4;
  if('\'' != 39) return 5;
  if('"' != 34) return 6;
  if('\n' != 10) return 7;
  if('\\' != 92) return 8;
  if(' ' != 32) return 9;

  return 0;
}
