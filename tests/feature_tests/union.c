int main() {
  union A *q;

  union A {
    int a_int_1;
    int a_int_2;
    int *a_ptr;
    union B {
      int b_int_one;
      long b_long;
    } nested_union;
    struct C {
      int c_int;
      long c_long;
    } nested_struct;
    long a_long_1;
  } a;

  q = &a;
  void* p1 = q + 1;
  char* p2 = p1;
  void* p3 = p2 - 4+4+8+8+4+8+8;

  union {};
  union I {} b;
  if(&b != (&b + 1)) return 2;

  a.a_int_1 = 10;
  if(a.a_int_1 != 10) return 3;
  a.a_ptr = &a.a_int_1;
  *a.a_ptr = 20;
  if(a.a_int_1 != 20) return 4;

  q = &a;
  (*q).a_int_2 = 15;
  if(a.a_int_2 != 15) return 5;
  if(q->a_int_2 != 15) return 11;

  p1 = q;
  p3 = &a.a_int_1;
  if(p1 != p3) return 6;

  a.nested_union.b_long = 10;
  if(a.nested_union.b_long != 10) return 7;
  if((*(&a.nested_union)).b_long != 10) return 8;
  if((&a.nested_union)->b_long != 10) return 12;

  long* p_val = &a.nested_union.b_long;
  if(*p_val != 10) return 9;

  *p_val = 20;
  if(a.nested_union.b_long != 20) return 10;

  union A array[10];
  array[3].nested_union.b_int_one = 3;
  if(array[3].nested_union.b_int_one != 3) return 13;
  if((&array[0] + 3)->nested_union.b_int_one != 3) return 14;

  union D {
    unsigned short a;
    unsigned int b;
  } u;
  u.b = 4294967295;
  if(u.a != 65535) return 15;
}
