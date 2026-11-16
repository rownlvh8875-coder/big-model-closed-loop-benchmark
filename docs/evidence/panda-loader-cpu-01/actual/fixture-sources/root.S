.text
.global _start
.type _start,@function
_start:
 andq $-16,%rsp
 call cpu_probe_value@PLT
 movl %eax,%edi
 movl $60,%eax
 syscall
.size _start,.-_start
.section .note.GNU-stack,"",@progbits
