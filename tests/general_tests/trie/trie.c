/********************************************************************

 An implementation of a trie, very loosely based off the
 CS50 pset 5 (https://docs.cs50.net/2017/x/psets/5/pset5.html).

********************************************************************/

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

struct node {
  struct node* next[27];
  int complete;
};

int main() {
  // constants due to shivyc limitations
  int sizeof_node = 27 * 8 + 4;
  int true = 1;
  int false = 0;

  // create the root node
  struct node* root = malloc(sizeof_node);
  for(int i = 0; i < 27; i++) root->next[i] = 0;
  root->complete = true;

  ////////////////////////////
  //        LOAD WORDS      //
  ////////////////////////////

  char* dictionary = "tests/general_tests/trie/words.txt";

  void* f = fopen(dictionary, "r");

  struct node** n = &root;
  char c;

  while((c = fgetc(f)) + 1 != 0) {
    if(c == '\n') {
      (*n)->complete = true;
      n = &root;
    }
    else {
      if(c == '\'') n = &((*n)->next[26]);
      else n = &((*n)->next[c - 'a']);

      if(!(*n)) {
        *n = malloc(sizeof_node);
        (*n)->complete = false;
        for(int i = 0; i < 27; i++) (*n)->next[i] = 0;
      }
    }
  }

  // finish processing the current word if needed
  if(!(*n)->complete) {
    (*n)->complete = true;
    n = &root;
  }

  fclose(f);

  ////////////////////////////
  //        TEST WORDS      //
  ////////////////////////////

  int NUM_WORDS = 10;
  char* words[10];
  words[0] = "doctor";
  words[1] = "they're";
  words[2] = "many";
  words[3] = "market";
  words[4] = "populate";
  words[5] = "proper";
  words[6] = "motion";
  words[7] = "notaword";
  words[8] = "notawordeither";
  words[9] = "notawordeithereither";

  for(int word_num = 0; word_num < NUM_WORDS; word_num++) {
    char* word = words[word_num];

    struct node* n = root;
    for(int i = 0, len = strlen(word); i < len; i++) {
      if(word[i] == '\'') n = n->next[26];
      else n = n->next[tolower(word[i]) - 'a'];

      if(!n) break;
    }

    if(!n || !n->complete) {
      printf("cannot find word %s\n", word);
    } else {
      printf("found word %s\n", word);
    }
  }
}
