/* CPython 3.12-specific, read-only layout introspection plus real dict calls.
 * Never modifies CPython's dictionary internals. */
#define Py_BUILD_CORE
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <internal/pycore_dict.h>
#include <limits.h>
#include "../../perfmark/perfmark.h"

static PyObject *snapshot(PyObject *self, PyObject *arg) {
    (void)self;
    if (!PyDict_CheckExact(arg)) {
        PyErr_SetString(PyExc_TypeError, "expected exact dict"); return NULL;
    }
    PyDictObject *d = (PyDictObject *)arg;
    PyDictKeysObject *k = d->ma_keys;
    if (d->ma_values || k->dk_kind != DICT_KEYS_GENERAL) {
        PyErr_SetString(PyExc_ValueError, "study supports combined general-key tables only"); return NULL;
    }
    Py_ssize_t capacity = DK_SIZE(k), width = ((Py_ssize_t)1 << k->dk_log2_index_bytes)/capacity;
    PyObject *indices = PyList_New(capacity), *entries = PyList_New(k->dk_nentries);
    if (!indices || !entries) { Py_XDECREF(indices); Py_XDECREF(entries); return NULL; }
    for (Py_ssize_t i = 0; i < capacity; ++i) {
        int64_t ix;
        switch (width) {
        case 1: ix = ((int8_t *)k->dk_indices)[i]; break;
        case 2: ix = ((int16_t *)k->dk_indices)[i]; break;
        case 4: ix = ((int32_t *)k->dk_indices)[i]; break;
        case 8: ix = ((int64_t *)k->dk_indices)[i]; break;
        default: Py_DECREF(indices); Py_DECREF(entries); PyErr_SetString(PyExc_ValueError, "index width"); return NULL;
        }
        PyObject *value = PyLong_FromLongLong(ix);
        if (!value) { Py_DECREF(indices); Py_DECREF(entries); return NULL; }
        PyList_SET_ITEM(indices, i, value);
    }
    PyDictKeyEntry *e = DK_ENTRIES(k);
    for (Py_ssize_t i = 0; i < k->dk_nentries; ++i) {
        PyObject *entry = e[i].me_value ? Py_BuildValue("LO", (long long)e[i].me_hash, e[i].me_key) : Py_NewRef(Py_None);
        if (!entry) { Py_DECREF(indices); Py_DECREF(entries); return NULL; }
        PyList_SET_ITEM(entries, i, entry);
    }
    return Py_BuildValue("{s:n,s:n,s:n,s:n,s:n,s:N,s:N}",
                         "used", d->ma_used, "capacity", capacity, "width", width,
                         "usable", k->dk_usable, "nentries", k->dk_nentries,
                         "indices", indices, "entries", entries);
}

static PyObject *measure(PyObject *self, PyObject *args) {
    (void)self;
    const char *region;
    PyObject *dict, *key, *labels, *features;
    int repeats, insert;
    if (!PyArg_ParseTuple(args, "sOOOOii", &region, &dict, &key, &labels, &features, &repeats, &insert)) return NULL;
    if (!PyDict_CheckExact(dict) || !PyTuple_Check(labels) || !PyTuple_Check(features) ||
        PyTuple_GET_SIZE(labels) != PyTuple_GET_SIZE(features) || PyTuple_GET_SIZE(labels) > INT_MAX ||
        repeats < 1 || (insert && repeats != 1)) {
        PyErr_SetString(PyExc_ValueError, "invalid measurement arguments"); return NULL;
    }
    int n = (int)PyTuple_GET_SIZE(labels);
    const char **names = PyMem_Calloc((size_t)n, sizeof(*names));
    int64_t *values = PyMem_Calloc((size_t)n, sizeof(*values));
    if (n && (!names || !values)) { PyMem_Free(names); PyMem_Free(values); return PyErr_NoMemory(); }
    for (int i = 0; i < n; ++i) {
        names[i] = PyUnicode_AsUTF8(PyTuple_GET_ITEM(labels, i));
        values[i] = PyLong_AsLongLong(PyTuple_GET_ITEM(features, i));
        if (PyErr_Occurred()) { PyMem_Free(names); PyMem_Free(values); return NULL; }
    }
    PyObject *seven = PyLong_FromLong(7);
    if (!seven) { PyMem_Free(names); PyMem_Free(values); return NULL; }
    long checksum = 0;
    int error = 0;
    perfmark_begin_v(region, n, names, values);
    if (insert) {
        error = PyDict_SetItem(dict, key, seven);
    } else {
        for (int i = 0; i < repeats; ++i) {
            PyObject *result = PyDict_GetItemWithError(dict, key);
            if (result) checksum += PyLong_AsLong(result);
            else if (PyErr_Occurred()) { error = -1; break; }
        }
    }
    perfmark_end(region);
    Py_DECREF(seven);
    PyMem_Free(names);
    PyMem_Free(values);
    if (error) return NULL;
    return PyLong_FromLong(checksum);
}

static PyMethodDef methods[] = {
    {"snapshot", snapshot, METH_O, "Read a combined CPython dictionary's actual table layout."},
    {"measure", measure, METH_VARARGS, "Measure actual dictionary lookup or insertion."},
    {NULL, NULL, 0, NULL}
};
static struct PyModuleDef module = {PyModuleDef_HEAD_INIT, "_hash_study", NULL, -1, methods, NULL, NULL, NULL, NULL};
PyMODINIT_FUNC PyInit__hash_study(void) { return PyModule_Create(&module); }
