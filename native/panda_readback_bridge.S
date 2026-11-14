/* Capture the original SysV7 arguments before any C prologue changes registers. */
.text
.globl pb_entry
.type pb_entry,@function
pb_entry:
  .cfi_startproc
  subq $88,%rsp
  .cfi_def_cfa_offset 96
  movl %edi,0(%rsp)
  movl %esi,4(%rsp)
  movl %edx,8(%rsp)
  movl %ecx,12(%rsp)
  movl %r8d,16(%rsp)
  movl %r9d,20(%rsp)
  movq 96(%rsp),%rax
  movq %rax,24(%rsp)
  movq 88(%rsp),%rax
  movq %rax,32(%rsp)
  movq %rbx,40(%rsp)
  movq %rbp,48(%rsp)
  movq %r12,56(%rsp)
  movq %r15,64(%rsp)
  leaq 88(%rsp),%rax
  movq %rax,72(%rsp)
  movq %rsp,%rdi
  call pb_dispatch
  addq $88,%rsp
  .cfi_def_cfa_offset 8
  ret
  .cfi_endproc
.size pb_entry,.-pb_entry
.section .note.GNU-stack,"",@progbits
