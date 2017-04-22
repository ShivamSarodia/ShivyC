int main() {
  int a = 5;

  a--;
  if(a != 4) return 1;
  if(a-- != 4) return 2;
  if(--a != 2) return 3;
  if(++a != 3) return 4;
  if(a++ != 3) return 5;

  a = 5;
  int* b = &a;
  (*b)++;
  if(a != 6) return 6;
  if((*b)++ != 6) return 7;
  if(--*b != 6) return 8;

  int arr[5];
  arr[0] = 10;
  if(++arr[0] != 11) return 9;
  if(arr[0] != 11) return 10;

  int* p = &a;
  if(p++ != &a) return 11;
  if(++p != &a + 2) return 12;
  if(p-- != &a + 2) return 13;
  if(--p - &a != 0) return 14;
}
