int main() {
  int array[2+3];
  if(&array != &array) return 1;
  if(array != array) return 2;
  if(&array[0] != &array[0]) return 13;

  if(&array[0] != (void*)array) return 13;
  if(&array[3] != &array[0] + 3) return 14;
  if(&array + 1 != (void*)(&array[0] + 5)) return 15;

  int array2[5];
  if(&array2 != &array2) return 3;
  if(array2 != array2) return 4;
  if(&array == &array2) return 5;
  if(array == array2) return 6;

  int array3[6];
  if(array == array3) return 7;
  if(&array == (void*)&array3) return 8;

  unsigned int array4[5];
  if(&array == (void*)&array4) return 9;
  if(array == (void*)array4) return 10;

  *array = 15;
  if(*array != 15) return 11;

  *(array + 2) = 20;
  if(*(array + 2) != 20) return 12;

  if(array[0] != 15) return 16;
  if(array[2] != 20) return 17;
  if((array+4)[-2] != 20) return 21;

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

  void *void_p1, *void_p2;
  char *p1, *p2;

  void_p1 = (&array5[0] + 1);
  void_p2 = &array5[0];
  p1 = void_p1;
  p2 = void_p2;

  p2 = p2 + 6 * 4;
  if(p1 != p2) {
    return 20;
  }


  int power_of_two_arr[10][10];
  power_of_two_arr[3][4] = 10;
  if(power_of_two_arr[3][4] != 10) return 21;

  return 0;
}
