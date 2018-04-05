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

  if('\0' != 0) return 10;
  if('\40' != 32) return 11;
  if('\100' != 64) return 12;
  if('\x9' != 9) return 13;
  if('\x67' != 103) return 14;
  if('\x7A' != 122) return 15;
  if('\x5a' != 90) return 16;
  if('\x00000021' != 33) return 17;

  if(strcmp("\x68\145\x6c\154\x6F", "hello")) return 18;
  if(strcmp("12\63", "123")) return 19;
  if(strcmp("\06123", "123")) return 20;
  if(strcmp("\578", "/8")) return 21;
  if(strcmp("\x2fg", "/g")) return 22;
  if(strcmp("\x", "\x")) return 23;

  return 0;
}
