/* Deliberately correct and incorrect event declarations. Markers never wait. */
#include <pthread.h>
#include <semaphore.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "perfmark.h"

static sem_t ready_b, ready_c;
static const char *mode;
static uint64_t generation = 1;
static void *producer_c(void *unused) {
    (void)unused;
    perfmark_begin("C", "n", 1);
    usleep(10000);
    perfmark_event_publish(2, generation);
    sem_post(&ready_c);
    perfmark_end("C");
    return NULL;
}
static void *producer_b(void *unused) {
    (void)unused;
    perfmark_begin("B", "n", 1);
    if (!strcmp(mode, "chain")) {
        sem_wait(&ready_c);
        perfmark_event_waited(2, generation);
    } else {
        usleep(!strcmp(mode, "wrong-pair") ? 200000 : 10000);
    }
    perfmark_event_publish(1, generation);
    sem_post(&ready_b);
    perfmark_end("B");
    return NULL;
}
int main(int argc, char **argv) {
    /* Attach before publishing threads or synchronization objects exist. */
    perfmark_begin("capture", "n", 1); perfmark_end("capture");
    mode = argc > 1 ? argv[1] : "correct";
    int conditional = !strcmp(mode, "conditional");
    for (int i = 0; i < (conditional ? 4 : 1); ++i) {
        generation = (uint64_t)i + 1;
        sem_init(&ready_b, 0, 0); sem_init(&ready_c, 0, 0);
        pthread_t b, c;
        int has_c = !strcmp(mode, "wrong-pair") || !strcmp(mode, "chain");
        int need = conditional ? i % 2 : 1;
        if (has_c) pthread_create(&c, NULL, producer_c, NULL);
        if (need) pthread_create(&b, NULL, producer_b, NULL);
        perfmark_begin("A", "need", need);
        /* The condition belongs to the original program, not the annotation. */
        if (need) {
            uint64_t event = !strcmp(mode, "wrong-pair") ? 2 : 1;
            if (!strcmp(mode, "missing-wait")) usleep(200000); /* BUG: no real wait */
            else sem_wait(&ready_b);
            if (strcmp(mode, "omitted") != 0)
                perfmark_event_waited(event, generation);
        }
        perfmark_end("A");
        if (need) pthread_join(b, NULL);
        if (has_c) pthread_join(c, NULL);
        sem_destroy(&ready_b); sem_destroy(&ready_c);
    }
    return 0;
}
