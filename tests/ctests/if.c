// Return: 30

int main() {
  // False literal condition
  if(0) return 1;

  // False variable condition
  int a;
  a = 0;
  if(a) return 2;

  // False variable equality condition
  int b; b = 10;
  int c; c = 11;
  if(b == c) return 3;

  // False variable inequality
  if(b != b) return 4;

  // True variable inequality
  if(b != c) {


    // False literal computation condition
    if(b * 0) {
      return 4;
    }

    // False literal equality condition
    if(3 == 4) {
      return 5;
    }

    // False literal inequality condition
    if(3 != 3) {
      return 6;
    }

    // False half-literal inequality condition
    b = 3;
    if(b != 3) {
      return 7;
    }

    // Valid conditions with computations
    int ret1; int ret2; int ret3;
    if(b == 3) {
      if(b != 15) {
        ret1 = 10;
        if(3 == 3) {
          ret2 = 10 + ret1;
          if(5) {
            ret3 = ret2 + 10;
            return ret3;
          }
        }
      }
    }
  }

  return 8;
}
