/* DSIQ streaming monomial-frame reconstruction. No quantum library.
 * q0 is LSB. Caller supplies validated internal frame coefficients and Pauli
 * images. Output is limited to the caller's block; no full-state allocation.
 */
#include <stdint.h>
#include <stddef.h>
#include <math.h>
#include <stdlib.h>
typedef struct {double re,im;} C;
typedef struct {uint64_t x,z;unsigned p;} Pauli;
static C mul(C a,C b){return (C){a.re*b.re-a.im*b.im,a.re*b.im+a.im*b.re};}
static unsigned parity(uint64_t x){return (unsigned)__builtin_parityll(x);}
static Pauli combine(Pauli a,Pauli b){return (Pauli){a.x^b.x,a.z^b.z,(a.p+b.p+2*parity(a.z&b.x))&3};}
/* n<=63 due to native index interface. No arbitrary-width limitation on JS mode.
 * groups: offsets in packed complex coefficient array, wire index lists.
 * All arrays are caller-owned; output range checked before writes. */
int dsiq_frame_block(unsigned n,uint64_t start,size_t count,uint64_t offset,unsigned gamma,
 double gr,double gi,const uint64_t *xs,const uint64_t *zs,const unsigned *ps,
 unsigned groups,const unsigned *sizes,const unsigned *wires,const size_t *offsets,
 size_t coefficient_count,const C *coeff,C *out){
 if(n<1||n>63||gamma>=8||!groups||groups>n||!isfinite(gr)||!isfinite(gi)||count>1048576||(!out&&count)||!coeff||!xs||!zs||!ps||!sizes||!wires||!offsets)return 2;
 const uint64_t N=UINT64_C(1)<<n; if(start>N||count>N-start||offset>=N)return 2;
 uint64_t seen=0;unsigned used=0;for(unsigned g=0;g<groups;g++){unsigned w=sizes[g];if(!w||w>24||w>n-used||offsets[g]>coefficient_count||((size_t)1<<w)>coefficient_count-offsets[g])return 2;for(unsigned j=0;j<w;j++){unsigned q=wires[used++];if(q>=n||(seen&(UINT64_C(1)<<q)))return 2;seen|=UINT64_C(1)<<q;}}if(used!=n)return 2;
 static const C phase[4]={{1,0},{0,1},{-1,0},{0,-1}};const double h=sqrt(0.5); const C eighth[8]={{1,0},{h,-h},{0,-1},{-h,-h},{-1,0},{-h,h},{0,1},{h,h}}; C global=mul((C){gr,gi},eighth[gamma]);
 unsigned chunks=(n+7)/8; Pauli tab[8][256];for(unsigned t=0;t<chunks;t++){tab[t][0]=(Pauli){0,0,0};for(unsigned u=1;u<256;u++){unsigned b=(unsigned)__builtin_ctz(u),q=8*t+b;Pauli p=q<n?(Pauli){xs[q],zs[q],ps[q]}:(Pauli){0,0,0};if(p.x>=N||p.z>=N||p.p>3)return 2;tab[t][u]=combine(tab[t][u&(u-1)],p);}}
 for(size_t i=0;i<count;i++){uint64_t x=start+i;Pauli p={0,0,0};for(unsigned t=0;t<chunks;t++)p=combine(p,tab[t][(x>>(8*t))&255]);uint64_t shift=offset^p.x;C v=mul(global,phase[(4-((p.p+2*parity(p.z&offset))&3))&3]);unsigned j=0;for(unsigned g=0;g<groups;g++){size_t k=0;for(unsigned b=0;b<sizes[g];b++)k|=(size_t)((shift>>wires[j++])&1)<<b;C a=coeff[offsets[g]+k],w=mul(v,a);if((v.re!=0||v.im!=0)&&(a.re!=0||a.im!=0)&&w.re==0&&w.im==0)return 4;v=w;}if(!isfinite(v.re)||!isfinite(v.im))return 3;out[i]=v;}
 return 0;
}
