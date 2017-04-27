int main() {
  char* test = "\"\\\n\\t";

  if(test[0] != 34) return 1;
  if(test[1] != 92) return 2;
  if(test[2] != 10) return 3;
  if(test[3] != 92) return 4;
  if(test[4] != 116) return 5;
  if(test[5] != 0) return 6;
}
