int main() {
  void* p;

  // error: sizeof argument cannot have incomplete type
  sizeof(*p);

  // error: sizeof argument cannot have incomplete type
  sizeof(void);

  // error: sizeof argument cannot have incomplete type
  sizeof(struct S);

  // error: sizeof argument cannot have function type
  sizeof(main);
}
