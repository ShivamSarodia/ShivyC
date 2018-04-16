int f() {
  return 3;
}

// error: non-constant initializer for variable with static storage duration
int a = f();

int main() { }
