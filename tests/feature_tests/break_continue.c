int main() {
  while(1) {
    break;
  }

  while(1) break;

  for(;;) {
    1 + 1;
    break;
    2 + 2;
  }

  int i = 0;
  for(i = 0; i != 10; i++) {
    if(i == 5) break;

    continue;
    i--;
  }

  if(i != 5) return 1;

  int count = 0;
  for(i = 0; i != 10; i++) {
    count++;
    while(1) {
      break;
    }
  }

  if(count != 10) return 2;
}
