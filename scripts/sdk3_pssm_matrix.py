"""Finite rows through Panda's published unaligned-to-aligned copy constructor."""
import math

def matrix_rows(core,matrix):
    aligned=core.LMatrix4f(matrix)
    rows=[[float(aligned.getCell(row,column)) for column in range(4)] for row in range(4)]
    if not all(math.isfinite(value) for row in rows for value in row):raise ValueError('nonfinite PSSM owner matrix')
    return rows
