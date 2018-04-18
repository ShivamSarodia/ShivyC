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

int int_ret() {
  int a = 3;
  // force `a` to conflict with RAX
  a = 3 / a;
  // must emit `mov` because `a` is not in RAX
  return a;
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

const int return_const() {
  return 4;
}

int ptr_value(const int* p) {
  return *p;
}

int sum_array(int a[][2], int len) {
  int sum = 0;
  for(int i = 0; i < len; i++) {
    for(int j = 0; j < 2; j++) {
      sum += a[i][j];
    }
  }
  return sum;
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

  int a = return_const();
  if(a != 4) return 10;

  if(ptr_value(&a) != 4) return 11;
  const int* p = &a;
  if(ptr_value(&a) != 4) return 12;

  int arr1[2][2];
  arr1[0][0] = 1;
  arr1[0][1] = 1;
  arr1[1][0] = 1;
  arr1[1][1] = 1;
  if(sum_array(arr1, 2) != 4) return 13;
}
