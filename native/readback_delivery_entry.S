.text
.globl rd_read_pixels
.type rd_read_pixels,@function
rd_read_pixels:
  /* A tail jump keeps the original Panda returnPC, stack argument and R12/R15. */
  jmp *rd_read_target(%rip)
.size rd_read_pixels,.-rd_read_pixels
.section .note.GNU-stack,"",@progbits
