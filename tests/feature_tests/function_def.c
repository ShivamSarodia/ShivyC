int add(int a, long b) {
  return a + b;
}

// test static variables with same name
int counter1() {
  static int i;
  return i++;
}

int counter2() {
  static int i;
  return i++;
}

// defined in function_def_helper.c
int helper_ret_5(void);
int helper_ret_6();

int helper;
void void_exit() {
  helper = 3;
}

void void_ret() {
  helper = 5;
  return;
  helper = 6;
}

int array_sum(int arr[3]) {
  int sum = 0;
  for(int i = 0; i < 3; i++) {
    sum += arr[i];
  }
  return sum;
}

int call_function(int f(int, long), int arg1, int arg2) {
  return f(arg1, arg2);
}

int main() {
  if(add(3, 4) != 7) return 1;
  if(add(helper_ret_5(), 4) != 9) return 2;
  if(add(helper_ret_6(), 5) != 11) return 3;

  for(int i = 0; i < 5; i++) {
    if(counter1() != i) return 4;
    if(counter2() != i) return 5;
  }

  void_exit();
  if(helper != 3) return 6;

  void_ret();
  if(helper != 5) return 7;

  int arr[3];
  arr[0] = 1;
  arr[1] = 2;
  arr[2] = 3;
  if(array_sum(arr) != 6) return 8;

  if(call_function(add, 5, 6) != 11) return 9;
}
