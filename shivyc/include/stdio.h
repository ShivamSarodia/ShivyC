typedef unsigned long size_t;
typedef struct __FILE_STRUCT FILE;

void     clearerr(FILE *);
char    *ctermid(char *);
int      fclose(FILE *);
FILE    *fdopen(int, const char *);
int      feof(FILE *);
int      ferror(FILE *);
int      fflush(FILE *);
int      fgetc(FILE*);
char    *fgets(char *, int, FILE*);
int      fileno(FILE*);
void     flockfile(FILE*);
FILE    *fopen(const char *, const char *);
int      fprintf(); // vargargs not yet implemented
int      fputc(int, FILE*);
int      fputs(const char *, FILE*);
size_t   fread(void *, size_t, size_t, FILE *);
FILE    *freopen(const char *, const char *, FILE *);
int      fscanf(); // vargargs not yet implemented
int      fseek(FILE *, long, int);
long     ftell(FILE *);
int      ftrylockfile(FILE *);
void     funlockfile(FILE *);
size_t fwrite(const void *, size_t, size_t, FILE*);
int      getc(FILE*);
int      getchar(void);
int      getc_unlocked(FILE *);
int      getchar_unlocked(void);
// removed in C11
// char    *gets(char *);
int      getw(void *);
int      pclose(void *);
void     perror(const char *);
void    *popen(const char *, const char *);
int      printf(); // vargargs not yet implemented
int      putc(int, FILE*);
int      putchar(int);
int      putc_unlocked(int, FILE*);
int      putchar_unlocked(int);
int      puts(const char *);
int      putw(int, FILE*);
int      remove(const char *);
int      rename(const char *, const char *);
void     rewind(FILE *);
int      scanf(); // vargargs not yet implemented
void     setbuf(FILE*, char *);
int      setvbuf(FILE*, char *, int, size_t);
int      snprintf();  // vargargs not yet implemented
int      sprintf();  // vargargs not yet implemented
int      sscanf(); // vargargs not yet implemented
char    *tempnam(const char *, const char *);
FILE    *tmpfile(void);
char    *tmpnam(char *);
int      ungetc(int, FILE*);

extern void* stdin;
extern void* stdout;
extern void* stderr;
