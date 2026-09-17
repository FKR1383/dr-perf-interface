#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "rodinia/kmeans.h"
#include "perfmark/perfmark.h"

static void fail(const char *message)
{
    fprintf(stderr, "%s\n", message);
    exit(1);
}

static void *allocate(size_t bytes)
{
    void *p = malloc(bytes);
    if (!p) fail("allocation failed");
    return p;
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

static float **matrix(int rows, int cols)
{
    float **m = allocate((size_t)rows * sizeof(*m));
    m[0] = allocate((size_t)rows * cols * sizeof(**m));
    for (int i = 1; i < rows; ++i) m[i] = m[0] + (size_t)i * cols;
    return m;
}

static void release_matrix(float **m)
{
    free(m[0]);
    free(m);
}

/* Generate fresh coordinates outside the measured region. The family label
 * describes the generator, not program state passed to the clustering kernel. */
static float **make_points(int npoints, int nfeatures, int nclusters,
                           int family, uint32_t *seed)
{
    float **feature = matrix(npoints, nfeatures);
    for (int i = 0; i < npoints; ++i) {
        float axis = 2.0f * uniform(seed) - 1.0f;
        for (int j = 0; j < nfeatures; ++j) {
            float noise = 2.0f * uniform(seed) - 1.0f;
            if (family == 0) {
                /* Separated blobs, with one initial center from each blob. */
                feature[i][j] = 8.0f * (i % nclusters) + 0.25f * noise;
            } else if (family == 1) {
                feature[i][j] = 4.0f * noise;  /* Uniform cloud. */
            } else {
                /* Elongated correlated cloud. */
                feature[i][j] = (j == 0 ? 32.0f : 2.0f / (j + 1)) * axis
                                + 0.25f * noise;
            }
        }
    }
    return feature;
}

__attribute__((noinline))
static float **cluster_region(float **feature, int nfeatures, int npoints,
                               int nclusters, float threshold, int *membership)
{
    /* EVALUATION_STATES_BEGIN */
    const char *names[] = {"npoints", "nfeatures", "nclusters"};
    const int64_t values[] = {npoints, nfeatures, nclusters};
    perfmark_begin_v("cluster", 3, names, values);
    /* EVALUATION_STATES_END */
    float **clusters = kmeans_clustering(feature, nfeatures, npoints, nclusters,
                                        threshold, membership);
    perfmark_end("cluster");
    return clusters;
}

/* Check a converged Lloyd fixed point independently of the upstream helpers:
 * nearest-center assignments, centroid means, finite values, and SSE. */
static double check_result(float **feature, float **clusters, int *membership,
                            int npoints, int nfeatures, int nclusters)
{
    double *sums = calloc((size_t)nclusters * nfeatures, sizeof(*sums));
    int *counts = calloc((size_t)nclusters, sizeof(*counts));
    if (!sums || !counts) fail("validation allocation failed");
    double sse = 0.0;
    for (int c = 0; c < nclusters; ++c)
        for (int j = 0; j < nfeatures; ++j)
            if (!isfinite(clusters[c][j])) fail("nonfinite centroid");
    for (int i = 0; i < npoints; ++i) {
        int assigned = membership[i];
        if (assigned < 0 || assigned >= nclusters) fail("invalid membership");
        double chosen = 0.0;
        for (int j = 0; j < nfeatures; ++j) {
            double d = (double)feature[i][j] - clusters[assigned][j];
            chosen += d * d;
            sums[(size_t)assigned * nfeatures + j] += feature[i][j];
        }
        for (int c = 0; c < nclusters; ++c) {
            double distance = 0.0;
            for (int j = 0; j < nfeatures; ++j) {
                double d = (double)feature[i][j] - clusters[c][j];
                distance += d * d;
            }
            if (chosen > distance + 0.00001 * (1.0 + chosen))
                fail("assignment is not nearest to final centroid");
        }
        ++counts[assigned];
        sse += chosen;
    }
    for (int c = 0; c < nclusters; ++c) {
        if (!counts[c]) continue;  /* Upstream retains an empty cluster's center. */
        for (int j = 0; j < nfeatures; ++j) {
            double mean = sums[(size_t)c * nfeatures + j] / counts[c];
            if (fabs(mean - clusters[c][j]) > 0.00005 * (1.0 + fabs(mean)))
                fail("centroid is not the mean of its assigned points");
        }
    }
    free(sums);
    free(counts);
    if (!isfinite(sse)) fail("nonfinite objective");
    return sse;
}

static void self_test(void)
{
    float **feature = matrix(4, 1);
    int membership[4];
    const float points[] = {-10.0f, -9.0f, 9.0f, 10.0f};
    memcpy(feature[0], points, sizeof(points));
    float **clusters = kmeans_clustering(feature, 1, 4, 2, 0.0f, membership);
    double sse = check_result(feature, clusters, membership, 4, 1, 2);
    if (fabs(sse - 1.0) > 0.00001 || membership[0] != membership[1]
        || membership[2] != membership[3] || membership[0] == membership[2])
        fail("two-cluster known-answer check failed");
    release_matrix(clusters);
    clusters = kmeans_clustering(feature, 1, 4, 1, 0.0f, membership);
    sse = check_result(feature, clusters, membership, 4, 1, 1);
    if (fabs(sse - 362.0) > 0.00001 || fabs(clusters[0][0]) > 0.00001)
        fail("one-cluster known-answer check failed");
    release_matrix(clusters);
    for (int i = 0; i < 4; ++i) feature[i][0] = 3.0f;
    clusters = kmeans_clustering(feature, 1, 4, 2, 0.0f, membership);
    if (check_result(feature, clusters, membership, 4, 1, 2) != 0.0)
        fail("duplicate-point and empty-cluster check failed");
    release_matrix(clusters);
    release_matrix(feature);
    puts("passed known-answer, duplicate-point, and empty-cluster checks");
}

static uint32_t positive_number(const char *text)
{
    char *end;
    errno = 0;
    unsigned long value = strtoul(text, &end, 10);
    if (errno || end == text || *end || !value || value > UINT32_MAX)
        fail("expected a positive 32-bit integer");
    return (uint32_t)value;
}

int main(int argc, char **argv)
{
    uint32_t shapes = 24, shape_seed = 17, data_seed = 7;
    if (argc == 2 && !strcmp(argv[1], "--self-test")) {
        self_test();
        return 0;
    }
    for (int i = 1; i < argc; i += 2) {
        if (i + 1 == argc) fail("option is missing a value");
        uint32_t value = positive_number(argv[i + 1]);
        if (!strcmp(argv[i], "--shapes")) shapes = value;
        else if (!strcmp(argv[i], "--shape-seed")) shape_seed = value;
        else if (!strcmp(argv[i], "--data-seed")) data_seed = value;
        else fail("usage: program [--shapes N] [--shape-seed N] [--data-seed N]");
    }
    if (shapes > 40) fail("at most 40 shapes (120 region calls) are supported");
    const int dimensions[] = {2, 4, 8, 16};
    const int centers[] = {2, 4, 8, 16};
    int used[57] = {0};
    for (uint32_t shape = 0; shape < shapes; ++shape) {
        unsigned slot;
        do { slot = next_random(&shape_seed) % 57; } while (used[slot]);
        used[slot] = 1;
        int npoints = 256 + 32 * (int)slot;
        int nfeatures = dimensions[next_random(&shape_seed) % 4];
        int nclusters = centers[next_random(&shape_seed) % 4];
        for (int family = 0; family < 3; ++family) {
            float **feature = make_points(npoints, nfeatures, nclusters, family, &data_seed);
            int *membership = allocate((size_t)npoints * sizeof(*membership));
            float **clusters = cluster_region(feature, nfeatures, npoints, nclusters,
                                                0.0f, membership);
            double sse = check_result(feature, clusters, membership,
                                       npoints, nfeatures, nclusters);
            printf("shape=%u family=%d npoints=%d nfeatures=%d nclusters=%d sse=%.9g\n",
                   shape, family, npoints, nfeatures, nclusters, sse);
            release_matrix(clusters);
            free(membership);
            release_matrix(feature);
        }
    }
    return 0;
}
