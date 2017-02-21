// Issue: 8: warning: implicit declaration of function 'isalpha'
// Issue: 9: warning: implicit declaration of function 'isalpha'
// Issue: 15: warning: implicit declaration of function 'div'

int main() {
  // Try out a few function calls from standard library.

  if(isalpha(65)) { // 'A'
    if(isalpha(52)) return 2; // '4'

    // This is super ratchet, but works for now. The div function
    // accepts two integers and returns a struct. It turns out the
    // quotient of this struct is returned in the integer return
    // register, so this test works.
    if(div(50, 5) != 10) {
      return 3;
    }

    return 0;
  }

  return 1;
}
