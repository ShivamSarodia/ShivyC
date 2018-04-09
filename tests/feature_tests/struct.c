int main() {
  struct A *q;

  struct A {
    int a_int_one;
    struct B {
      int b_int_one;
      long b_long;
      int b_int_two;
    } b_struct;
    int a_int_two, *a_ptr;
    int;
  } a;

  q = &a;
  void* p1 = q + 1;
  char* p2 = p1;

  // this is a hacky test to check sizeof(struct A)
  void* p3 = p2 - 8*4;

  if(p3 != q) return 1;

  struct {};
  struct I {} b;
  if(&b != (&b + 1)) return 2;

  //////////////////////////

  a.a_int_one = 10;
  if(a.a_int_one != 10) return 3;
  a.a_ptr = &a.a_int_one;
  *a.a_ptr = 20;
  if(a.a_int_one != 20) return 4;

  q = &a;
  (*q).a_int_two = 15;
  if(a.a_int_two != 15) return 5;
  if(q->a_int_two != 15) return 11;

  p1 = q;
  p3 = &a.a_int_one;
  if(p1 != p3) return 6;

  a.b_struct.b_long = 10;
  if(a.b_struct.b_long != 10) return 7;
  if((*(&a.b_struct)).b_long != 10) return 8;
  if((&a.b_struct)->b_long != 10) return 12;

  long* p_val = &a.b_struct.b_long;
  if(*p_val != 10) return 9;

  *p_val = 20;
  if(a.b_struct.b_long != 20) return 10;

  struct A array[10];
  array[3].b_struct.b_int_one = 3;
  if(array[3].b_struct.b_int_one != 3) return 13;
  if((&array[0] + 3)->b_struct.b_int_one != 3) return 14;


  // Check with array members
  struct F {
    int array[10];
  };

  struct F array2[10];
  array2[5].array[5] = 3;
  if(array2[5].array[5] != 3) return 15;

  // Check anonymous struct
  struct {
    int a;
  } s;
  s.a = 3;
  if(s.a != 3) return 16;


  // Check with union members
  struct C {
    int c_int;
    union D {
      int d_int;
      long d_long;
    } nested_union_d;
    union E {
      int e_int;
    } nested_union_e;
  };
}
