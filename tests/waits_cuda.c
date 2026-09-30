#include <stdint.h>
#include <stddef.h>
#ifdef EMULATOR
#include <semaphore.h>
static sem_t completion;
static void *handle = (void *)0x1234;
static volatile unsigned long scratch;
int cudaEventCreate(void **event) { *event=handle; return sem_init(&completion,0,0); }
int cudaEventRecord(void *event, void *stream) {
    for (int i=0;i<5000;i++) scratch+=i;
    return sem_post(&completion);
}
int cudaEventSynchronize(void *event) { return sem_wait(&completion); }
int cudaEventDestroy(void *event) { return sem_destroy(&completion); }
int cudaStreamCreate(void **stream) { *stream=(void *)0x7654; return 0; }
int cudaMemcpyAsync(void *dst, const void *src, size_t bytes, int kind, void *stream) {
    scratch+=bytes; return 0;
}
int cudaStreamSynchronize(void *stream) { return 0; }
int cudaStreamDestroy(void *stream) { return 0; }
#else
#include "perfmark.h"
extern int cudaEventCreate(void **), cudaEventRecord(void *, void *);
extern int cudaEventSynchronize(void *), cudaEventDestroy(void *);
extern int cudaStreamCreate(void **), cudaStreamSynchronize(void *), cudaStreamDestroy(void *);
extern int cudaMemcpyAsync(void *, const void *, size_t, int, void *);
int main(void) {
    perfmark_begin("app", "n", 1);
    for (int i=0;i<2;i++) {
        void *event;
        cudaEventCreate(&event);
        perfmark_begin(i ? "upload" : "download", "n", 1);
        cudaEventRecord(event, (void *)(uintptr_t)(42+i));
        perfmark_end(i ? "upload" : "download");
        perfmark_begin("consume", "n", 1);
        cudaEventSynchronize(event);
        perfmark_end("consume");
        cudaEventDestroy(event);
    }
    void *stream;
    cudaStreamCreate(&stream);
    perfmark_begin("copy", "bytes", 32);
    cudaMemcpyAsync(NULL, NULL, 32, 0, stream);
    perfmark_end("copy");
    perfmark_begin("consume_stream", "bytes", 32);
    cudaStreamSynchronize(stream);
    perfmark_end("consume_stream");
    cudaStreamDestroy(stream);
    perfmark_end("app");
    return 0;
}
#endif
