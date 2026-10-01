/* Only ordinary region annotations. Waits/dependencies are not annotated. */
#include <pthread.h>
#include <semaphore.h>
#include <stdio.h>
#include <unistd.h>
#include "perfmark.h"

static sem_t done;
static volatile unsigned long result;
static void *produce(void *arg) {
    long n = (long)arg;
    perfmark_begin("decode", "units", n);
    unsigned long value = 0;
    for (long i = 0; i < 1000*n; i++) value += i;
    result = value;
    sem_post(&done);
    perfmark_end("decode");
    return NULL;
}
int main(void) {
    perfmark_begin("workload", "n", 1);
    for (long n = 1; n <= 3; n++) {
        perfmark_begin("consume", "items", n);
        for (long i = 0; i < n; i++) {
            pthread_t thread;
            sem_init(&done, 0, 0);
            pthread_create(&thread, NULL, produce, (void *)n);
            /* Usually allow completion before the consumer reaches the wait.
             * A delay at decode's sem_post exposes the same dependency. */
            usleep(20000);
            sem_wait(&done);
            pthread_join(thread, NULL);
            sem_destroy(&done);
        }
        perfmark_end("consume");
    }
    pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
    perfmark_begin("metadata", "entries", 1);
    pthread_mutex_lock(&mutex);
    result++;
    pthread_mutex_unlock(&mutex);
    perfmark_end("metadata");
    perfmark_end("workload");
    printf("result=%lu\n", result);
    return 0;
}
