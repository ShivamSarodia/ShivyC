int main() {
  int a = 0;

  if(0) {
    return 1;
  } else {
    a = 10;
  }

  // Verify correct branch was taken
  if(a != 10) return 2; else {

    // Verify proper dangling-else parsing
    if(0) if(1) return 4; else return 5;

    return 0;
  }

  return 6;
}
