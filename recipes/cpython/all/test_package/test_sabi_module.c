#include <Python.h>

static PyObject *
spam_sabi_answer(PyObject *self, PyObject *args)
{
    return PyLong_FromLong(42);
}

static PyMethodDef spam_sabi_methods[] = {
    {"answer", spam_sabi_answer, METH_NOARGS, "Return the answer."},
    {NULL, NULL, 0, NULL}
};

#ifdef Py_TARGET_ABI3T

PyABIInfo_VAR(spam_sabi_abi_info);

static PySlot spam_sabi_slots[] = {
    PySlot_DATA(Py_mod_abi, &spam_sabi_abi_info),
    PySlot_STATIC_DATA(Py_mod_name, "spam_sabi"),
    PySlot_STATIC_DATA(Py_mod_methods, spam_sabi_methods),
    PySlot_DATA(Py_mod_gil, Py_MOD_GIL_NOT_USED),
    PySlot_END
};

PyMODEXPORT_FUNC
PyModExport_spam_sabi(void)
{
    return spam_sabi_slots;
}

#else

static struct PyModuleDef spam_sabi_module = {
    PyModuleDef_HEAD_INIT,
    "spam_sabi",
    NULL,
    -1,
    spam_sabi_methods
};

PyMODINIT_FUNC
PyInit_spam_sabi(void)
{
    return PyModule_Create(&spam_sabi_module);
}

#endif
