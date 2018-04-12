typedef int a;
// error: expected declaration specifier at 'a'
int function(int a, a b) {
  return a;
}
