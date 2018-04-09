int isalpha(int);
int div(); // test function prototype

int strcmp(char*, char*);
char* strcpy(char*, char*);
char* strncpy(char*, char*, long);
int atoi(char *str);

int signal(int, int(int));

int main() {
  // Try out a few function calls from standard library.

  _Bool b;

  b = isalpha(65); // 'A'
  if(b != 1) return 1;

  // Coax the return IL value of atoi to be assigned to a register
  // that is not RAX, so we can test the `mov` operation that moves a
  // return value from RAX to the spot its IL value is stored in.
  if(1/atoi("1") != 1) return 14;

  b = isalpha(52);
  if(b != 0) return 2;

  // This is super ratchet, but works for now. The div function
  // accepts two integers and returns a struct. It turns out the
  // quotient of this struct is returned in the integer return
  // register, so this test works.
  char c1 = 50, c2 = 5;
  if(div(c1, c2) != 10) return 3;

  char str1[6], str2[6];
  strcpy(str1, "hello");
  strcpy(str2, "hello");
  if(strcmp(str1, str2)) return 4;

  // doing (vp=___) is basically a ratchet cast to avoid pointer
  // errors
  void *vp;
  if(strcmp((vp=str1), str2)) return 13;

  str2[3] = 102;
  if(strcmp(str1, str2) != 6) return 5;

  strcpy(str2, "hey");
  char* out = strncpy(str1, str2, 3);
  if(strcmp(str1, "heylo")) return 6;

  int (*f2)(int) = isalpha;
  if(f2(5)) return 12;

  // test passing a function to a function
  signal(0, isalpha);

  return 0;
}
