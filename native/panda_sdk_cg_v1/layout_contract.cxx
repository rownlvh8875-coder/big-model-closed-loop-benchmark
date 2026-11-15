// Compile to an object containing DATA only. Never link or execute this object.
#include "glgsg.h"
#include "shader.h"
#include "graphicsPipe.h"
#include <cstdint>
#ifndef HAVE_CG
#error The candidate must include genuine Cg definitions.
#endif
#ifndef _GLIBCXX_USE_CXX11_ABI
#error Explicit libstdc++ ABI selection is required.
#endif
extern "C" __attribute__((used, section(".panda_cg_layout")))
const std::uint64_t panda_cg_layout[] = {
  0x50414e4441434731ULL, 1, sizeof(void *), _GLIBCXX_USE_CXX11_ABI, 1,
  sizeof(Shader::ShaderCaps), sizeof(GraphicsPipe), sizeof(GraphicsStateGuardian),
  sizeof(GLGraphicsStateGuardian),
  __builtin_offsetof(GLGraphicsStateGuardian, _gl_vendor),
  __builtin_offsetof(GLGraphicsStateGuardian, _gl_version_major),
  __builtin_offsetof(GLGraphicsStateGuardian, _gl_version_minor)
};
