/********************************************************************

 An implementation of a trie, loosely based off the CS50 pset 5
 (https://docs.cs50.net/2017/x/psets/5/pset5.html).

********************************************************************/

#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdbool.h>

typedef struct node {
  struct node* next[27];
  int complete;
} Node;

// Load words from the given dictionary into a trie.
Node* load(const char* dictionary);

// Check whether a word is in the given trie.
bool check(Node* root, const char* word);

int main() {
  Node* trie = load("tests/general_tests/trie/words.txt");

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
    if(check(trie, word)) {
      printf("found word %s\n", word);
    } else {
      printf("cannot find word %s\n", word);
    }
  }
}

Node* load(const char* dictionary) {
  Node* root = malloc(sizeof(Node));
  for(int i = 0; i < 27; i++) root->next[i] = 0;
  root->complete = 1;

  FILE* f = fopen(dictionary, "r");

  Node** n = &root;
  char c;

  while((c = fgetc(f)) + 1 != 0) {
    if(c == '\n') {
      (*n)->complete = 1;
      n = &root;
    }
    else {
      if(c == '\'') n = &((*n)->next[26]);
      else n = &((*n)->next[c - 'a']);

      if(!(*n)) {
        *n = malloc(sizeof(Node));
        (*n)->complete = 0;
        for(int i = 0; i < 27; i++) (*n)->next[i] = 0;
      }
    }
  }

  // finish processing the current word if needed
  if(!(*n)->complete) {
    (*n)->complete = 1;
    n = &root;
  }

  fclose(f);

  return root;
}

bool check(Node* root, const char* word) {
  Node* n = root;
  for(int i = 0, len = strlen(word); i < len; i++) {
    if(word[i] == '\'') n = n->next[26];
    else n = n->next[tolower(word[i]) - 'a'];

    if(!n) break;
  }

  return n && n->complete;
}
