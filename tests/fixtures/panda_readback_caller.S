/* CPU-only caller with the pinned Panda local-stack/register layout. */
.text
.globl pb_fixture_call
.type pb_fixture_call,@function
pb_fixture_call:
  pushq %rbx
  pushq %rbp
  pushq %r12
  pushq %r13
  pushq %r14
  pushq %r15
  subq $72,%rsp
  movq %rdi,%r10
  movq %r10,56(%rsp)
  movl 64(%r10),%eax
  movl %eax,4(%rsp)
  movl 68(%r10),%eax
  movl %eax,24(%rsp)
  movq 32(%r10),%rbx
  movq 40(%r10),%rbp
  movq 48(%r10),%r12
  movq 56(%r10),%r15
  movq $0x13579,%r13
  movq $0x24680,%r14
  movl 0(%r10),%edi
  movl 4(%r10),%esi
  movl 8(%r10),%edx
  movl 12(%r10),%ecx
  movl 16(%r10),%r8d
  movl 20(%r10),%r9d
  movq 24(%r10),%rax
  subq $8,%rsp
  pushq %rax
  call pb_entry
.globl pb_fixture_return
pb_fixture_return:
  addq $16,%rsp
  movq 56(%rsp),%r10
  xorl %eax,%eax
  cmpq 32(%r10),%rbx
  jne 1f
  cmpq 40(%r10),%rbp
  jne 1f
  cmpq 48(%r10),%r12
  jne 1f
  cmpq 56(%r10),%r15
  jne 1f
  cmpq $0x13579,%r13
  jne 1f
  cmpq $0x24680,%r14
  jne 1f
  movl $1,%eax
1:
  addq $72,%rsp
  popq %r15
  popq %r14
  popq %r13
  popq %r12
  popq %rbp
  popq %rbx
  ret
.size pb_fixture_call,.-pb_fixture_call
.section .note.GNU-stack,"",@progbits
