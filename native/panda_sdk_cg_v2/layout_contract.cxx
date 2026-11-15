// Compile only; the complete parent object and every initializer remain inert DATA.
#include "glgsg.h"
#include "shader.h"
#include "graphicsPipe.h"
#include <cstdint>
#if !defined(HAVE_CG) || !defined(HAVE_EIGEN) || !defined(LINMATH_ALIGN)
#error Real Cg/Eigen and effective aligned linmath are required.
#endif
#if !defined(_GLIBCXX_USE_CXX11_ABI) || _GLIBCXX_USE_CXX11_ABI != 0
#error Explicit libstdc++ ABI0 is required.
#endif
static_assert(alignof(LVecBase4f)==16, "16-byte vector alignment required");
static_assert(MEMORY_HOOK_ALIGNMENT==16, "16-byte allocator alignment required");
extern "C" __attribute__((used,section(".panda_cg_layout_v2")))
const std::uint64_t panda_cg_layout_v2[] = {
  0x50414e4441434732ULL, 2, sizeof(void *), _GLIBCXX_USE_CXX11_ABI, 1,
  sizeof(Shader::ShaderCaps), sizeof(GraphicsPipe), sizeof(GraphicsStateGuardian),
  sizeof(GLGraphicsStateGuardian),
  __builtin_offsetof(GLGraphicsStateGuardian,_gl_vendor),
  __builtin_offsetof(GLGraphicsStateGuardian,_gl_version_major),
  __builtin_offsetof(GLGraphicsStateGuardian,_gl_version_minor),
  1, 1, alignof(LVecBase4f), MEMORY_HOOK_ALIGNMENT
};
