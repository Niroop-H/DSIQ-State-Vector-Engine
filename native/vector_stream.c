/* DSIQ bounded full-vector traversal comparator, validation utility only.
 * Every basis coefficient is independently reconstructed from two supplied
 * contiguous-factor representations. No dense output array or disk paging.
 * The source of each factor representation is documented by the caller.
 */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#define NMAX 30
#define MAX_FACTOR_COEFF 32768u
typedef struct {double r,i;} C;
static C a[MAX_FACTOR_COEFF],b[MAX_FACTOR_COEFF];
static unsigned sizes[NMAX],offset[NMAX],groups,used;
static uint64_t visits,nonzero;static double max_sq,max_rel_sq;
static C mul(C x,C y){return (C){x.r*y.r-x.i*y.i,x.r*y.i+x.i*y.r};}
static void traverse(int g,C x,C y){unsigned off=offset[g],size=sizes[g];if(g){for(unsigned i=0;i<size;i++)traverse(g-1,mul(x,a[off+i]),mul(y,b[off+i]));return;}
 for(unsigned i=0;i<size;i++){C u=mul(x,a[off+i]),v=mul(y,b[off+i]);double dr=u.r-v.r,di=u.i-v.i,e=dr*dr+di*di,m=v.r*v.r+v.i*v.i;if(e>max_sq)max_sq=e;if(m>0){double rel=e/m;if(rel>max_rel_sq)max_rel_sq=rel;nonzero++;}visits++;}}
int main(void){unsigned n;if(scanf("%u%u",&n,&groups)!=2||n<1||n>NMAX||groups<1||groups>n)return 2;unsigned width=0;for(unsigned g=0;g<groups;g++){unsigned w;if(scanf("%u",&w)!=1||w<1||w>15)return 2;unsigned s=1u<<w;if(s>MAX_FACTOR_COEFF-used)return 2;sizes[g]=s;offset[g]=used;width+=w;for(unsigned i=0;i<s;i++){C *x=&a[used+i],*y=&b[used+i];if(scanf("%lf%lf%lf%lf",&x->r,&x->i,&y->r,&y->i)!=4||!isfinite(x->r)||!isfinite(x->i)||!isfinite(y->r)||!isfinite(y->i))return 2;}used+=s;}if(width!=n)return 2;struct timespec t0,t1;clock_gettime(CLOCK_MONOTONIC,&t0);traverse((int)groups-1,(C){1,0},(C){1,0});clock_gettime(CLOCK_MONOTONIC,&t1);double ms=(t1.tv_sec-t0.tv_sec)*1000.0+(t1.tv_nsec-t0.tv_nsec)*1e-6;printf("{\"qubits\":%u,\"amplitudesCompared\":%llu,\"nonzeroReferenceAmplitudes\":%llu,\"maxAbsoluteError\":%.17g,\"maxRelativeError\":%.17g,\"coefficientBytesBoth\":%zu,\"staticCoefficientArenaBytesBoth\":%zu,\"executionMs\":%.17g}\n",n,(unsigned long long)visits,(unsigned long long)nonzero,sqrt(max_sq),sqrt(max_rel_sq),2*(size_t)used*sizeof(C),sizeof a+sizeof b,ms);return visits==(UINT64_C(1)<<n)?0:2;}
