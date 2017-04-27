int main() {
  int a;
  {
    {
      int b;
      b = 10;
      a = b;
    }

    {

    }
  }

  return a - 10;
}
