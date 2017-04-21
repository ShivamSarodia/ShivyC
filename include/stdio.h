void     clearerr(void *);
char    *ctermid(char *);
int      fclose(void *);
void    *fdopen(int, char *);
int      feof(void *);
int      ferror(void *);
int      fflush(void *);
int      fgetc(void *);
char    *fgets(char *, int, void *);
int      fileno(void *);
void     flockfile(void *);
void    *fopen(char *, char *);
int      fprintf(); // vargargs not yet implemented
int      fputc(int, void *);
int      fputs(char *, void *);
long     fread(void *, long, long, void *);
void    *freopen(char *, char *, void *);
int      fscanf(); // vargargs not yet implemented
int      fseek(void *, long, int);
long     ftell(void *);
int      ftrylockfile(void *);
void     funlockfile(void *);
long     fwrite(void *, long, long, void *);
int      getc(void *);
int      getchar(void);
int      getc_unlocked(void *);
int      getchar_unlocked(void);
char    *gets(char *);
int      getw(void *);
int      pclose(void *);
void     perror(char *);
void    *popen(char *, char *);
int      printf(); // vargargs not yet implemented
int      putc(int, void *);
int      putchar(int);
int      putc_unlocked(int, void *);
int      putchar_unlocked(int);
int      puts(char *);
int      putw(int, void *);
int      remove(char *);
int      rename(char *, char *);
void     rewind(void *);
int      scanf(); // vargargs not yet implemented
void     setbuf(void *, char *);
int      setvbuf(void *, char *, int, long);
int      snprintf();  // vargargs not yet implemented
int      sprintf();  // vargargs not yet implemented
int      sscanf(); // vargargs not yet implemented
char    *tempnam(char *, char *);
void    *tmpfile(void);
char    *tmpnam(char *);
int      ungetc(int, void *);

extern void* stdin;
extern void* stdout;
extern void* stderr;
