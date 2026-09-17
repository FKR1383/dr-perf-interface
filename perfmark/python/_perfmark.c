/* _perfmark: C extension so a Python marker costs a few hundred instructions
 * instead of the ~10K of ctypes plus a Python-level `with` protocol.
 *
 *   Region(name: bytes, states: list[(bytes, int)]|None, extra: list[(bytes, bytes)]|None)
 *     __enter__ -> perfmark_begin / perfmark_begin_v (+ perfmark_state for each extra pair)
 *     __exit__  -> perfmark_end
 *     state(name, value)
 *   begin(name, state_name, value) / end(name) / state(name, value)
 *
 * The calls go through the PLT into libperfmark.so, which is what the drperf
 * client wraps.  Built by build.sh into build/_perfmark.so; perfmark.py falls
 * back to ctypes when it is missing.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <limits.h>
#include "../perfmark.h"

static const char *
as_cstr(PyObject *o)
{
    if (PyBytes_Check(o))
        return PyBytes_AS_STRING(o);
    if (PyUnicode_Check(o))
        return PyUnicode_AsUTF8(o);
    PyErr_SetString(PyExc_TypeError, "expected str or bytes");
    return NULL;
}

typedef struct {
    PyObject_HEAD
    PyObject *name;   /* bytes */
    PyObject *states; /* list of (bytes, int): declared states, all part of the key; or NULL */
    PyObject *extra;  /* list of (bytes, bytes) or NULL */
} RegionObject;

static int
check_pairs(PyObject *lst, int int_values, const char *what)
{
    Py_ssize_t i;
    if (!PyList_Check(lst)) {
        PyErr_Format(PyExc_TypeError, "%s must be a list of (bytes, %s)", what, int_values ? "int" : "bytes");
        return -1;
    }
    for (i = 0; i < PyList_GET_SIZE(lst); i++) {
        PyObject *t = PyList_GET_ITEM(lst, i);
        if (!PyTuple_Check(t) || PyTuple_GET_SIZE(t) != 2 || !PyBytes_Check(PyTuple_GET_ITEM(t, 0)) ||
            (int_values ? !PyLong_Check(PyTuple_GET_ITEM(t, 1)) : !PyBytes_Check(PyTuple_GET_ITEM(t, 1)))) {
            PyErr_Format(PyExc_TypeError, "%s must be a list of (bytes, %s)", what, int_values ? "int" : "bytes");
            return -1;
        }
    }
    return 0;
}

static int
Region_init(RegionObject *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = { "name", "states", "extra", NULL };
    PyObject *name, *states = Py_None, *extra = Py_None;
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "S|OO", kwlist, &name, &states, &extra))
        return -1;
    if (states != Py_None && check_pairs(states, 1, "states") < 0)
        return -1;
    if (extra != Py_None && check_pairs(extra, 0, "extra") < 0)
        return -1;
    Py_INCREF(name);
    Py_XSETREF(self->name, name);
    if (states == Py_None) {
        Py_CLEAR(self->states);
    } else {
        Py_INCREF(states);
        Py_XSETREF(self->states, states);
    }
    if (extra == Py_None) {
        Py_CLEAR(self->extra);
    } else {
        Py_INCREF(extra);
        Py_XSETREF(self->extra, extra);
    }
    return 0;
}

static void
Region_dealloc(RegionObject *self)
{
    Py_XDECREF(self->name);
    Py_XDECREF(self->states);
    Py_XDECREF(self->extra);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

#define STACK_KEY_STATES 8 /* allocation-free fast path, not a limit */

static PyObject *
Region_enter(RegionObject *self, PyObject *Py_UNUSED(ignored))
{
    const char *name = PyBytes_AS_STRING(self->name);
    Py_ssize_t n = self->states != NULL ? PyList_GET_SIZE(self->states) : 0;
    if (n == 0) {
        perfmark_begin(name, "", 0);
    } else if (n == 1) {
        PyObject *t = PyList_GET_ITEM(self->states, 0);
        int64_t value = PyLong_AsLongLong(PyTuple_GET_ITEM(t, 1));
        if (PyErr_Occurred())
            return NULL;
        perfmark_begin(name, PyBytes_AS_STRING(PyTuple_GET_ITEM(t, 0)), value);
    } else {
        const char *stack_names[STACK_KEY_STATES];
        int64_t stack_vals[STACK_KEY_STATES];
        const char **names = stack_names;
        int64_t *vals = stack_vals;
        Py_ssize_t i;
        if (n > INT_MAX) {
            PyErr_SetString(PyExc_OverflowError, "number of states exceeds the C marker ABI");
            return NULL;
        }
        if (n > STACK_KEY_STATES) {
            names = PyMem_Calloc((size_t)n, sizeof(*names));
            vals = PyMem_Calloc((size_t)n, sizeof(*vals));
            if (names == NULL || vals == NULL) {
                PyMem_Free(names);
                PyMem_Free(vals);
                return PyErr_NoMemory();
            }
        }
        for (i = 0; i < n; i++) {
            PyObject *t = PyList_GET_ITEM(self->states, i);
            names[i] = PyBytes_AS_STRING(PyTuple_GET_ITEM(t, 0));
            vals[i] = PyLong_AsLongLong(PyTuple_GET_ITEM(t, 1));
            if (PyErr_Occurred())
                break;
        }
        if (!PyErr_Occurred())
            perfmark_begin_v(name, (int)n, names, vals);
        if (n > STACK_KEY_STATES) {
            PyMem_Free(names);
            PyMem_Free(vals);
        }
        if (PyErr_Occurred())
            return NULL;
    }
    if (self->extra != NULL) {
        Py_ssize_t i;
        for (i = 0; i < PyList_GET_SIZE(self->extra); i++) {
            PyObject *t = PyList_GET_ITEM(self->extra, i);
            perfmark_state(PyBytes_AS_STRING(PyTuple_GET_ITEM(t, 0)),
                           PyBytes_AS_STRING(PyTuple_GET_ITEM(t, 1)));
        }
    }
    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject *
Region_exit(RegionObject *self, PyObject *Py_UNUSED(args))
{
    perfmark_end(PyBytes_AS_STRING(self->name));
    Py_RETURN_FALSE;
}

static PyObject *
Region_state(RegionObject *self, PyObject *args)
{
    PyObject *ko, *vo;
    const char *k, *v;
    if (!PyArg_ParseTuple(args, "OO", &ko, &vo))
        return NULL;
    if ((k = as_cstr(ko)) == NULL || (v = as_cstr(vo)) == NULL)
        return NULL;
    perfmark_state(k, v);
    Py_RETURN_NONE;
}

static PyMethodDef Region_methods[] = {
    { "__enter__", (PyCFunction)Region_enter, METH_NOARGS, "open the region" },
    { "__exit__", (PyCFunction)Region_exit, METH_VARARGS, "close the region" },
    { "state", (PyCFunction)Region_state, METH_VARARGS, "attach an extra state to the open region" },
    { NULL, NULL, 0, NULL }
};

static PyTypeObject RegionType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_perfmark.Region",
    .tp_basicsize = sizeof(RegionObject),
    .tp_itemsize = 0,
    .tp_dealloc = (destructor)Region_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_doc = "perfmark region (C fast path)",
    .tp_methods = Region_methods,
    .tp_init = (initproc)Region_init,
    .tp_new = PyType_GenericNew,
};

static PyObject *
mod_begin(PyObject *Py_UNUSED(m), PyObject *args)
{
    PyObject *no, *so = NULL;
    const char *name, *sname = "";
    long long value = 0;
    if (!PyArg_ParseTuple(args, "O|OL", &no, &so, &value))
        return NULL;
    if ((name = as_cstr(no)) == NULL)
        return NULL;
    if (so != NULL && (sname = as_cstr(so)) == NULL)
        return NULL;
    perfmark_begin(name, sname, value);
    Py_RETURN_NONE;
}

static PyObject *
mod_end(PyObject *Py_UNUSED(m), PyObject *args)
{
    PyObject *no;
    const char *name;
    if (!PyArg_ParseTuple(args, "O", &no))
        return NULL;
    if ((name = as_cstr(no)) == NULL)
        return NULL;
    perfmark_end(name);
    Py_RETURN_NONE;
}

static PyObject *
mod_state(PyObject *Py_UNUSED(m), PyObject *args)
{
    PyObject *ko, *vo;
    const char *k, *v;
    if (!PyArg_ParseTuple(args, "OO", &ko, &vo))
        return NULL;
    if ((k = as_cstr(ko)) == NULL || (v = as_cstr(vo)) == NULL)
        return NULL;
    perfmark_state(k, v);
    Py_RETURN_NONE;
}

static PyMethodDef mod_methods[] = {
    { "begin", mod_begin, METH_VARARGS, "begin(name, state_name='', value=0)" },
    { "end", mod_end, METH_VARARGS, "end(name)" },
    { "state", mod_state, METH_VARARGS, "state(name, value)" },
    { NULL, NULL, 0, NULL }
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT, "_perfmark", "perfmark markers, C fast path", -1, mod_methods,
};

PyMODINIT_FUNC
PyInit__perfmark(void)
{
    PyObject *m;
    if (PyType_Ready(&RegionType) < 0)
        return NULL;
    m = PyModule_Create(&moduledef);
    if (m == NULL)
        return NULL;
    Py_INCREF(&RegionType);
    if (PyModule_AddObject(m, "Region", (PyObject *)&RegionType) < 0) {
        Py_DECREF(&RegionType);
        Py_DECREF(m);
        return NULL;
    }
    return m;
}
