#include <stdint.h>
#include <string.h>
#include <errno.h>
struct lookup {char name[64];uint32_t active;};
void psd_lookup_begin(const char *name,struct lookup *p){(void)name;memset(p,0,sizeof(*p));}
void *psd_resolved(const struct lookup *p,void *value,uint32_t origin){(void)p;(void)origin;return value;}
extern void glDrawArrays(unsigned,int,int);
extern void glDrawElements(unsigned,int,unsigned,const void *);
extern void glDrawRangeElements(unsigned,unsigned,unsigned,int,unsigned,const void *);
extern void glDrawArraysInstanced(unsigned,int,int,int);
extern void glDrawElementsInstanced(unsigned,int,unsigned,const void *,int);
extern void glDrawElementsInstancedARB(unsigned,int,unsigned,const void *,int);
extern void glDrawArraysInstancedEXT(unsigned,int,int,int);
extern void glDrawElementsIndirect(unsigned,unsigned,const void *);
extern void glDrawArraysIndirect(unsigned,const void *);
static void *resolve(const char *name,void *value,int nested){struct lookup outer,inner;psd_lookup_begin(name,&outer);if(nested){psd_lookup_begin("glUnrelatedQuery",&inner);psd_resolved(&inner,(void *)1,2);}return psd_resolved(&outer,value,2);}
int fake_invoke(int kind,int nested){
 errno=EDOM;
 if(kind==0)glDrawArrays(4,17,31);
 else if(kind==1)glDrawElements(4,31,5125,(void *)(uintptr_t)0x12345000);
 else if(kind==2)((void(*)(unsigned,unsigned,unsigned,int,unsigned,const void*))resolve("glDrawRangeElements",glDrawRangeElements,nested))(4,17,53,31,5125,(void *)(uintptr_t)0x12345000);
 else if(kind==3)((void(*)(unsigned,int,int,int))resolve("glDrawArraysInstanced",glDrawArraysInstanced,nested))(4,17,31,7);
 else if(kind==4)((void(*)(unsigned,int,unsigned,const void*,int))resolve("glDrawElementsInstanced",glDrawElementsInstanced,nested))(4,31,5125,(void *)(uintptr_t)0x12345000,7);
 else if(kind==5)((void(*)(unsigned,int,unsigned,const void*,int))resolve("glDrawElementsInstancedARB",glDrawElementsInstancedARB,nested))(4,31,5125,(void *)(uintptr_t)0x12345000,7);
 else if(kind==6)((void(*)(unsigned,int,int,int))resolve("glDrawArraysInstancedEXT",glDrawArraysInstancedEXT,nested))(4,17,31,7);
 else if(kind==7)((void(*)(unsigned,unsigned,const void*))resolve("glDrawElementsIndirect",glDrawElementsIndirect,nested))(4,5125,(void *)(uintptr_t)0x12345000);
 else if(kind==8)((void(*)(unsigned,const void*))resolve("glDrawArraysIndirect",glDrawArraysIndirect,nested))(4,(void *)(uintptr_t)0x12345000);
 return errno;
}
