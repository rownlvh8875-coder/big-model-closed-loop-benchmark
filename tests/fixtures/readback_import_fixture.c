/* Link a CPU inspection fixture with unresolved names. Never load or execute it. */
#include <stdio.h>
extern void glReadPixels(void);
extern void glXCreateContext(void);
extern void glPixelStorei(void);
void pc_import_entry(void) { glReadPixels(); glXCreateContext(); puts("CPU ELF DATA ONLY"); }
void (*pc_import_address(void))(void) { return glPixelStorei; }
