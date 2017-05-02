/*******************************************************************************

 pi.c

 An obfuscated C program to print the first several digits of pi.

 Source: https://cs.uwaterloo.ca/~alopez-o/math-faq/mathtext/node12.html

******************************************************************************/

#include <stdio.h>

int main(){
  int a = 10000, b = 0, c=2800, d = 0, e = 0, f[2801], g = 0;
  for(; b-c;) f[b++]=a/5;
  for(; d=0, g=c*2; c-=14, printf("%.4d",e+d/a), e = d%a)
    for(b=c; d+=f[b]*a, f[b]=d%--g, d/=g-- ,--b; d*=b);
  printf("\n");
}
