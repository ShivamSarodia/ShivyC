void     clearerr(void *);
char    *ctermid(char *);
int      fclose(void *);
void    *fdopen(int, const char *);
int      feof(void *);
int      ferror(void *);
int      fflush(void *);
int      fgetc(void *);
char    *fgets(char *, int, void *);
int      fileno(void *);
void     flockfile(void *);
void    *fopen(const char *, const char *);
int      fprintf(); // vargargs not yet implemented
int      fputc(int, void *);
int      fputs(const char *, void *);
long     fread(void *, unsigned long, unsigned long, void *);
void    *freopen(const char *, const char *, void *);
int      fscanf(); // vargargs not yet implemented
int      fseek(void *, long, int);
long     ftell(void *);
int      ftrylockfile(void *);
void     funlockfile(void *);
unsigned long fwrite(const void *, unsigned long, unsigned long, void *);
int      getc(void *);
int      getchar(void);
int      getc_unlocked(void *);
int      getchar_unlocked(void);
// removed in C11
// char    *gets(char *);
int      getw(void *);
int      pclose(void *);
void     perror(const char *);
void    *popen(const char *, const char *);
int      printf(); // vargargs not yet implemented
int      putc(int, void *);
int      putchar(int);
int      putc_unlocked(int, void *);
int      putchar_unlocked(int);
int      puts(const char *);
int      putw(int, void *);
int      remove(const char *);
int      rename(const char *, const char *);
void     rewind(void *);
int      scanf(); // vargargs not yet implemented
void     setbuf(void *, char *);
int      setvbuf(void *, char *, int, unsigned long);
int      snprintf();  // vargargs not yet implemented
int      sprintf();  // vargargs not yet implemented
int      sscanf(); // vargargs not yet implemented
char    *tempnam(const char *, const char *);
void    *tmpfile(void);
char    *tmpnam(char *);
int      ungetc(int, void *);

extern void* stdin;
extern void* stdout;
extern void* stderr;
