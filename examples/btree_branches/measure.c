#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "../../perfmark/perfmark.h"

/* Measure the installed, unmodified BTrees extension, without a Python loop.
 * Argument conversion and PCV construction take place before the marker. */
static PyObject *measure(PyObject *self, PyObject *args) {
    (void)self;
    const char *region;
    PyObject *tree, *key, *labels, *features;
    int repeats;
    if (!PyArg_ParseTuple(args, "sOOOOi", &region, &tree, &key, &labels, &features, &repeats))
        return NULL;
    if (!PyTuple_Check(labels) || !PyTuple_Check(features) || repeats < 1 ||
        PyTuple_GET_SIZE(labels) != PyTuple_GET_SIZE(features) ||
        PyTuple_GET_SIZE(labels) > 4) {
        PyErr_SetString(PyExc_ValueError, "expected matching PCV tuples of at most four items");
        return NULL;
    }
    int k = (int)PyTuple_GET_SIZE(labels);
    const char *names[4];
    int64_t values[4];
    for (int i = 0; i < k; ++i) {
        names[i] = PyUnicode_AsUTF8(PyTuple_GET_ITEM(labels, i));
        values[i] = PyLong_AsLongLong(PyTuple_GET_ITEM(features, i));
        if (PyErr_Occurred()) return NULL;
    }
    long checksum = 0;
    perfmark_begin_v(region, k, names, values);
    for (int i = 0; i < repeats; ++i) {
        PyObject *result = PyObject_GetItem(tree, key);
        if (!result) { perfmark_end(region); return NULL; }
        checksum += PyLong_AsLong(result);
        Py_DECREF(result);
    }
    perfmark_end(region);
    return PyLong_FromLong(checksum);
}
static PyMethodDef methods[] = {
    {"measure", measure, METH_VARARGS, "Count repeated unmodified BTrees lookups."},
    {NULL, NULL, 0, NULL}
};
static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT, "_btree_measure", NULL, -1, methods, NULL, NULL, NULL, NULL
};
PyMODINIT_FUNC PyInit__btree_measure(void) { return PyModule_Create(&module); }
