"""Owner-checked CPU registry. No Panda imports, RAM reads or native admission.

native_binding() is private controller data. Call guard before each host window;
actual mapped code/handle lifetimes and event/receipt transport need qualification.
"""
import threading

class RegistryError(RuntimeError):pass

class CameraRegistry:
    def __init__(self,provider,nonce,*,max_windows=12):
        self._owner=threading.get_ident();self._busy=False;self._error=None;self._closed=False
        self._calls=0;self._guards=0;self._attempts=0;self._returns=0
        self._provider=provider;self._nonce=nonce;self._max=max_windows
        if type(nonce) is not bytes or len(nonce)!=32 or not any(nonce) or type(max_windows) is not int or not 1<=max_windows<=12:
            self._reject()
        try:
            self._env=provider.env;self._engine=self._env.engine;self._sensors=self._engine.sensors
            self._cameras=tuple(self._sensors[k] for k in ('bigbench_road','bigbench_wide'))
            self._textures=tuple(c.copy_texture for c in self._cameras)
            self._buffers=tuple(c.buffer for c in self._cameras)
            if any(a is b for a,b in ((self._cameras[0],self._cameras[1]),(self._textures[0],self._textures[1]),(self._buffers[0],self._buffers[1]))):self._reject()
            self._texture_handles=tuple(self._handle(t) for t in self._textures)
            self._buffer_handles=tuple(self._handle(t) for t in self._buffers)
            if len(set(self._texture_handles))!=2 or len(set(self._buffer_handles))!=2:self._reject()
            self._busy=True;self._gsg_refs,self._gsg=self._read_gsg();self._busy=False
        except BaseException as exc:
            self._error=type(exc).__name__
            if not isinstance(exc,Exception):raise
            raise RegistryError('registry registration failed') from exc

    def _reject(self):
        self._error='RegistryError';raise RegistryError('registry ownership, lifecycle or budget rejected')

    def _handle(self,obj):
        value=obj.this
        if type(value) is not int or not 0<value<2**64:self._reject()
        return value

    def _ready(self):
        if threading.get_ident()!=self._owner:self._reject()
        if self._closed or self._error is not None or self._busy:self._reject()

    def _owners(self):
        if self._provider.env is not self._env or self._env.engine is not self._engine or self._engine.sensors is not self._sensors:self._reject()
        for i,k in enumerate(('bigbench_road','bigbench_wide')):
            c=self._cameras[i]
            if self._sensors[k] is not c or c.copy_texture is not self._textures[i] or c.buffer is not self._buffers[i]:self._reject()
            if self._handle(self._textures[i])!=self._texture_handles[i] or self._handle(self._buffers[i])!=self._buffer_handles[i]:self._reject()

    def _read_gsg(self):
        methods=tuple(b.getGsg for b in self._buffers)
        if any(not callable(f) or getattr(f,'__self__',None) is not b for f,b in zip(methods,self._buffers)):self._reject()
        refs=[];handles=[]
        for f in methods:
            if self._error is not None:self._reject()
            self._attempts+=1;g=f();self._returns+=1
            if self._error is not None:self._reject()
            refs.append(g);handles.append(self._handle(g))
        if handles[0]!=handles[1]:self._reject()
        return tuple(refs),handles[0]

    def guard(self,host_call,requested_camera):
        self._ready()
        if type(host_call) is not int or host_call!=self._calls+1 or host_call>self._max or type(requested_camera) is not int or requested_camera!=(1 if host_call%2 else 2):self._reject()
        self._busy=True
        try:
            self._owners()
            if self._error is not None:self._reject()
            refs,gsg=self._read_gsg()
            if gsg!=self._gsg or any(self._handle(g)!=self._gsg for g in self._gsg_refs):self._reject()
            self._gsg_refs=refs;self._calls=host_call;self._guards+=1
        except BaseException as exc:
            self._error=type(exc).__name__
            if not isinstance(exc,Exception):raise
            raise RegistryError('registry guard failed') from exc
        finally:self._busy=False

    def native_binding(self):
        self._ready()
        self._busy=True
        try:
            self._owners()
            if self._error is not None or any(self._handle(g)!=self._gsg for g in self._gsg_refs):self._reject()
        except BaseException as exc:
            self._error=type(exc).__name__
            if not isinstance(exc,Exception):raise
            raise RegistryError('registry binding failed') from exc
        finally:self._busy=False
        return (*self._texture_handles,self._gsg)

    def descriptor(self):
        return dict(schema='readback-camera-registry-v1',nonce=self._nonce.hex(),roles=dict(road=1,wide=2),
                    max_windows=self._max,guards_returned=self._guards,getter_attempts=self._attempts,getter_returns=self._returns,
                    closed=self._closed,error=self._error,native_admission_proven=False,driver_state_proven=False,
                    actual_native_identity_proven=False)

    def close(self):
        if threading.get_ident()!=self._owner or self._busy:self._reject()
        self._closed=True
        self._provider=self._env=self._engine=self._sensors=None
        self._cameras=self._textures=self._buffers=self._gsg_refs=()
