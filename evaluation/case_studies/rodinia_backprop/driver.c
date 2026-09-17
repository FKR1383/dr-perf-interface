#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "rodinia/backprop.h"
#include "perfmark/perfmark.h"

extern BPNN *bpnn_create(int, int, int);
extern void bpnn_free(BPNN *);
extern void bpnn_train(BPNN *, float *, float *);

static void fail(const char *message)
{
    fprintf(stderr, "%s\n", message);
    exit(1);
}

static uint32_t next_random(uint32_t *state)
{
    uint32_t x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return *state = x;
}

static float uniform(uint32_t *state)
{
    return (float)(next_random(state) >> 8) / 16777216.0f;
}

static BPNN *make_network(int in, int hid, int out, uint32_t seed)
{
    BPNN *net = bpnn_create(in, hid, out);
    if (!net)
        fail("network allocation failed");
    for (int i = 0; i <= in; ++i)
        net->input_units[i] = uniform(&seed);
    for (int i = 0; i <= hid; ++i)
        net->hidden_units[i] = net->hidden_delta[i] = 0.0f;
    for (int i = 0; i <= out; ++i) {
        net->output_units[i] = net->output_delta[i] = 0.0f;
        net->target[i] = 0.1f + 0.8f * uniform(&seed);
    }
    float input_scale = 1.0f / sqrtf((float)(in + 1));
    float hidden_scale = 1.0f / sqrtf((float)(hid + 1));
    for (int i = 0; i <= in; ++i)
        for (int j = 0; j <= hid; ++j) {
            net->input_weights[i][j] = (2.0f * uniform(&seed) - 1.0f) * input_scale;
            net->input_prev_weights[i][j] = 0.0f;
        }
    for (int i = 0; i <= hid; ++i)
        for (int j = 0; j <= out; ++j) {
            net->hidden_weights[i][j] = (2.0f * uniform(&seed) - 1.0f) * hidden_scale;
            net->hidden_prev_weights[i][j] = 0.0f;
        }
    return net;
}

__attribute__((noinline))
static void train_region(BPNN *net, int steps, float *output_error, float *hidden_error)
{
    /* EVALUATION_STATES_BEGIN */
    perfmark_begin("train", "net->input_n", (int64_t)net->input_n);
    /* EVALUATION_STATES_END */
    for (int step = 0; step < steps; ++step)
        bpnn_train(net, output_error, hidden_error);
    perfmark_end("train");
}

static double checked_checksum(BPNN *net)
{
    double checksum = 0.0;
    for (int j = 1; j <= net->output_n; ++j) {
        float value = net->output_units[j];
        if (!isfinite(value) || value < 0.0f || value > 1.0f)
            fail("invalid output activation");
    }
    for (int i = 0; i <= net->input_n; ++i)
        for (int j = 1; j <= net->hidden_n; ++j) {
            if (!isfinite(net->input_weights[i][j]) || !isfinite(net->input_prev_weights[i][j]))
                fail("nonfinite input-layer weight");
            checksum += net->input_weights[i][j];
        }
    for (int i = 0; i <= net->hidden_n; ++i)
        for (int j = 1; j <= net->output_n; ++j) {
            if (!isfinite(net->hidden_weights[i][j]) || !isfinite(net->hidden_prev_weights[i][j]))
                fail("nonfinite hidden-layer weight");
            checksum += net->hidden_weights[i][j];
        }
    return checksum;
}

/* Independent scalar loss for the tiny numerical-gradient correctness check. */
static double tiny_loss(const BPNN *net)
{
    double hidden[3] = {1.0, 0.0, 0.0}, loss = 0.0;
    for (int j = 1; j <= 2; ++j) {
        double sum = net->input_weights[0][j];
        for (int i = 1; i <= 3; ++i)
            sum += (double)net->input_weights[i][j] * net->input_units[i];
        hidden[j] = 1.0 / (1.0 + exp(-sum));
    }
    for (int j = 1; j <= 2; ++j) {
        double sum = net->hidden_weights[0][j];
        for (int i = 1; i <= 2; ++i)
            sum += (double)net->hidden_weights[i][j] * hidden[i];
        double difference = net->target[j] - 1.0 / (1.0 + exp(-sum));
        loss += 0.5 * difference * difference;
    }
    return loss;
}

static double numerical_update(BPNN *net, float *weight, float momentum)
{
    float original = *weight;
    *weight = original + 0.001f;
    float plus = *weight;
    double right = tiny_loss(net);
    *weight = original - 0.001f;
    float minus = *weight;
    double left = tiny_loss(net);
    *weight = original;
    return original - ETA * (right - left) / (plus - minus) + MOMENTUM * momentum;
}

static void self_test(void)
{
    BPNN *net = make_network(3, 2, 2, 7);
    double expected_input[4][3], expected_hidden[3][3];
    /* Two steps check both backpropagation and the previous-step momentum. */
    for (int step = 0; step < 2; ++step) {
        for (int i = 0; i <= 3; ++i)
            for (int j = 1; j <= 2; ++j)
                expected_input[i][j] = numerical_update(net, &net->input_weights[i][j],
                                                        net->input_prev_weights[i][j]);
        for (int i = 0; i <= 2; ++i)
            for (int j = 1; j <= 2; ++j)
                expected_hidden[i][j] = numerical_update(net, &net->hidden_weights[i][j],
                                                         net->hidden_prev_weights[i][j]);
        float eo, eh;
        bpnn_train(net, &eo, &eh);
        for (int i = 0; i <= 3; ++i)
            for (int j = 1; j <= 2; ++j)
                if (fabs(net->input_weights[i][j] - expected_input[i][j]) > 0.00002)
                    fail("input weight disagrees with numerical gradient");
        for (int i = 0; i <= 2; ++i)
            for (int j = 1; j <= 2; ++j)
                if (fabs(net->hidden_weights[i][j] - expected_hidden[i][j]) > 0.00002)
                    fail("hidden weight disagrees with numerical gradient");
    }
    bpnn_free(net);
    puts("passed numerical-gradient and momentum checks");
}

static uint32_t positive_number(const char *text)
{
    char *end;
    errno = 0;
    unsigned long value = strtoul(text, &end, 10);
    if (errno || *end || *text == '-' || value == 0 || value > UINT32_MAX)
        fail("expected a positive 32-bit integer");
    return (uint32_t)value;
}

int main(int argc, char **argv)
{
    unsigned cases = 96;
    uint32_t shape_seed = 17, data_seed = 7;
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) {
        self_test();
        return 0;
    }
    for (int i = 1; i < argc; i += 2) {
        if (i + 1 == argc)
            fail("usage: program [--cases N] [--shape-seed N] [--data-seed N]");
        uint32_t value = positive_number(argv[i + 1]);
        if (strcmp(argv[i], "--cases") == 0) cases = value;
        else if (strcmp(argv[i], "--shape-seed") == 0) shape_seed = value;
        else if (strcmp(argv[i], "--data-seed") == 0) data_seed = value;
        else fail("unknown option");
    }
    if (cases > 120)
        fail("at most 120 cases are supported per invocation");
    const int hidden_sizes[] = {8, 16, 24, 32, 48, 64, 96, 128};
    const int output_sizes[] = {1, 2, 4, 8, 16, 32, 64};
    const int step_counts[] = {1, 2, 3, 4, 6, 8, 12, 16};
    unsigned char used_inputs[253] = {0};
    double checksum = 0.0;
    for (unsigned c = 0; c < cases; ++c) {
        unsigned slot;
        do { slot = next_random(&shape_seed) % 253; } while (used_inputs[slot]);
        used_inputs[slot] = 1;
        int in = 64 + 16 * (int)slot;
        int hid = hidden_sizes[next_random(&shape_seed) % 8];
        int out = output_sizes[next_random(&shape_seed) % 7];
        int steps = step_counts[next_random(&shape_seed) % 8];
        BPNN *net = make_network(in, hid, out, data_seed);
        float eo = 0.0f, eh = 0.0f;
        train_region(net, steps, &eo, &eh);
        if (!isfinite(eo) || !isfinite(eh))
            fail("nonfinite training error");
        double value = checked_checksum(net);
        checksum += value;
        printf("case=%u in=%d hid=%d out=%d steps=%d error=%.9g checksum=%.17g\n",
               c + 1, in, hid, out, steps, eo, value);
        bpnn_free(net);
    }
    printf("completed %u CPU training cases; checksum=%.17g\n", cases, checksum);
    return 0;
}
