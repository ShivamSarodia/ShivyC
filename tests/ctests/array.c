int main() {
  int array[5];
  if(&array != &array) return 1;
  if(array != array) return 2;

  int array2[5];
  if(&array2 != &array2) return 3;
  if(array2 != array2) return 4;
  if(&array == &array2) return 5;
  if(array == array2) return 6;

  int array3[6];
  if(array == array3) return 7;
  // Issue: 15: warning: comparison between distinct pointer types
  if(&array == &array3) return 8;

  unsigned int array4[5];
  // Issue: 19: warning: comparison between distinct pointer types
  if(&array == &array4) return 9;

  *array = 15;
  if(*array != 15) return 10;

  *(array + 2) = 20;
  if(*(array + 2) != 20) return 11;

  return 0;
}
