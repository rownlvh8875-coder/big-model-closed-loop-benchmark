/* Link a CPU inspection fixture with unresolved names. Never load or execute it. */
#include <stdio.h>
extern void glReadPixels(void);
extern void glXCreateContext(void);
extern void glPixelStorei(void);
void pc_import_entry(void) { glReadPixels(); glXCreateContext(); puts("CPU ELF DATA ONLY"); }
void (*pc_import_address(void))(void) { return glPixelStorei; }
/* Data relocations keep total relocations distinct from dynamic-symbol count. */
const char *pc_data_addresses[8] = {"CPU", "CPU", "CPU", "CPU", "CPU", "CPU", "CPU", "CPU"};
