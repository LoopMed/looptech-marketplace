"""memory-graph: local semantic recall + graph traversal over markdown memory files.

100% local. No data ever leaves the machine — embeddings are computed with a
local ONNX model via fastembed, and the vector/graph store is a local SQLite
file.
"""

__version__ = "0.1.0"
