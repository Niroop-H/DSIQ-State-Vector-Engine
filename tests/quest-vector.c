/* Build as USER_SOURCE with QuEST 3.7.0, CPU, double precision, single rank. */
#include "QuEST.h"
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

int main(void) {
    unsigned n, gates;
    if (sizeof(qreal) != sizeof(double) || scanf("%u %u", &n, &gates) != 2 ||
        n < 2 || n > 30 || gates > 100000) return 2;
#ifdef _WIN32
    _setmode(_fileno(stdout), _O_BINARY);
#endif
    QuESTEnv env = createQuESTEnv();
    if (env.numRanks != 1) return 2;
    Qureg reg = createQureg((int)n, env);
    initZeroState(reg);
    for (unsigned i = 0; i < gates; i++) {
        char name[12];
        int q, c;
        double angle;
        if (scanf("%11s %d %d %lf", name, &q, &c, &angle) != 4 ||
            q < 0 || q >= (int)n || c < -1 || c >= (int)n || c == q || !isfinite(angle)) return 2;
        if (c < 0 && !strcmp(name, "ry")) rotateY(reg, q, angle);
        else if (c < 0 && !strcmp(name, "rz")) rotateZ(reg, q, angle);
        else if (c < 0 && !strcmp(name, "x")) pauliX(reg,q);
        else if (c < 0 && !strcmp(name, "z")) pauliZ(reg,q);
        else if (c < 0 && (!strcmp(name,"project0") || !strcmp(name,"project1"))) {
            ComplexMatrix2 projector = {0};
            int outcome = name[7]-'0';
            projector.real[outcome][outcome] = 1;
            applyMatrix2(reg,q,projector);
        }
        else if (c < 0 && !strcmp(name, "s")) sGate(reg, q);
        else if (c >= 0 && !strcmp(name, "cx")) controlledNot(reg, c, q);
        else if (c >= 0 && !strcmp(name, "cz")) controlledPhaseFlip(reg, c, q);
        else if (c >= 0 && !strcmp(name, "swap")) swapGate(reg, c, q);
        else return 2;
    }
    static double block[8192];
    uint64_t total = UINT64_C(1) << n;
    for (uint64_t base = 0; base < total; base += 4096) {
        size_t count = total - base < 4096 ? (size_t)(total - base) : 4096;
        for (size_t j = 0; j < count; j++) {
            block[2*j] = reg.stateVec.real[base+j];
            block[2*j+1] = reg.stateVec.imag[base+j];
        }
        if (fwrite(block, 2*sizeof(double), count, stdout) != count) return 3;
    }
    destroyQureg(reg, env);
    destroyQuESTEnv(env);
    return fflush(stdout) != 0;
}
