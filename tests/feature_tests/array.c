int main() {
  int array[5];
  if(&array != &array) return 1;
  if(array != array) return 2;
  if(&array[0] != &array[0]) return 13;

  // warning: comparison between distinct pointer types
  if(&array[0] != &array) return 13;
  if(&array[3] != &array[0] + 3) return 14;
  // warning: comparison between distinct pointer types
  if(&array + 1 != &array[0] + 5) return 15;

  int array2[5];
  if(&array2 != &array2) return 3;
  if(array2 != array2) return 4;
  if(&array == &array2) return 5;
  if(array == array2) return 6;

  int array3[6];
  if(array == array3) return 7;
  // warning: comparison between distinct pointer types
  if(&array == &array3) return 8;

  unsigned int array4[5];
  // warning: comparison between distinct pointer types
  if(&array == &array4) return 9;
  // warning: comparison between distinct pointer types
  if(array == array4) return 10;

  *array = 15;
  if(*array != 15) return 11;

  *(array + 2) = 20;
  if(*(array + 2) != 20) return 12;

  if(array[0] != 15) return 16;
  if(array[2] != 20) return 17;

  // Test array subscripting
  array[1] = 35;
  array[3] = 10;
  4[array] = 1[array] + array[3];

  int sum = 0, i = 0;
  while(i != 5) {
    sum = sum + array[i];
    i = i + 1;
  }

  if(sum != 15 + 35 + 20 + 10 + 35 + 10) return 18;

  // Test multidimentional arrays
  int array5[5][6];
  array5[2][3] = 10;
  if(array5[2][3] != 10) return 19;

  void *p1, *p2;
  p1 = (&array5[0] + 1);
  p2 = &array5[0];
  p2 = p2 + 6 * 4;
  if(p1 != p2) {
    return 20;
  }

  return 0;
}
