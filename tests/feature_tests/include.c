#include "include_helper.h"
#include "include_helper_empty.h"

int main() {
  char* a = "test string";

  // Make sure the includes in include_helper.h were successful.
  isalpha(10);
  strcpy(a, a);
}
