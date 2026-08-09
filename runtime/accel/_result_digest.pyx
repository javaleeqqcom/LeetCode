# cython: language_level=3
# cython: boundscheck=False, wraparound=False, initializedcheck=False

"""CPython fast path for canonical scalar result digests."""

from cpython.bytes cimport PyBytes_FromStringAndSize
from libc.stdio cimport snprintf

import hashlib

from .fallback import digest_value as _fallback_digest_value


cpdef object digest_value(object index, object cid, object output, object error):
    cdef long long index_value
    cdef long long cid_value
    cdef long long output_value
    cdef char payload_buffer[96]
    cdef int payload_length
    cdef object payload
    cdef object digest_bytes

    if (
        error is None
        and type(index) is int
        and type(cid) is int
        and type(output) is int
    ):
        try:
            index_value = index
            cid_value = cid
            output_value = output
        except OverflowError:
            return _fallback_digest_value(index, cid, output, error)
        payload_length = snprintf(
            payload_buffer,
            sizeof(payload_buffer),
            b"[%lld,%lld,%lld,null]",
            index_value,
            cid_value,
            output_value,
        )
        if 0 <= payload_length < sizeof(payload_buffer):
            payload = PyBytes_FromStringAndSize(payload_buffer, payload_length)
            digest_bytes = hashlib.blake2b(payload, digest_size=16).digest()
            return int.from_bytes(digest_bytes, "big")
    return _fallback_digest_value(index, cid, output, error)
