namespace { struct state {int n;}; state S={}; }
extern "C" int increment(){return S.n++;}
