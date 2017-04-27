// error: expected "FILENAME" or <FILENAME> after include directive
#include
// error: expected "FILENAME" or <FILENAME> after include directive
#include blah
// error: missing terminating character for include filename
#include <hey there
// error: missing terminating character for include filename
#include "hey there
// error: extra tokens at end of include directive
#include "hi" lmao
