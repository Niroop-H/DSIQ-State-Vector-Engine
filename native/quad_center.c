/* IEEE binary128 centers. Build with GCC/quadmath, no fast-math.
 * Radius calculation and resource checks are performed by the Python caller. */
#include <quadmath.h>
#include <stdint.h>
#include <stddef.h>
#include <float.h>
#include <math.h>
typedef struct { __float128 r,i; } qc;
_Static_assert(sizeof(qc)==32,"binary128 storage mismatch");
int dsiq_qparse(qc *z,const char *r,const char *i,int p){z->r=ldexpq(strtoflt128(r,0),-p);z->i=ldexpq(strtoflt128(i,0),-p);return !finiteq(z->r)||!finiteq(z->i);}
int dsiq_qmag(size_t n,const qc *a,double *m){for(size_t j=0;j<n;j++){double r=(double)a[j].r,i=(double)a[j].i;if(!isfinite(r)||!isfinite(i)||(a[j].r!=0&&fabs(r)<DBL_MIN)||(a[j].i!=0&&fabs(i)<DBL_MIN))return 1;double v=hypot(r,i);if(!isfinite(v))return 1;m[j]=v?nextafter(v*(1+16*DBL_EPSILON),INFINITY):0;}return 0;}
int dsiq_qdot(size_t batch,size_t m,size_t k,size_t n,const qc *a,const qc*b,qc*z){for(size_t t=0;t<batch;t++)for(size_t i=0;i<m;i++)for(size_t j=0;j<n;j++){__float128 r=0,im=0;for(size_t h=0;h<k;h++){qc x=a[(t*m+i)*k+h],y=b[(t*k+h)*n+j];r+=x.r*y.r-x.i*y.i;im+=x.r*y.i+x.i*y.r;}if(!finiteq(r)||!finiteq(im))return 1;z[(t*m+i)*n+j]=(qc){r,im};}return 0;}
int dsiq_qproj(const qc *a,double *v){v[0]=(double)a->r;v[1]=(double)a->i;if(!isfinite(v[0])||!isfinite(v[1]))return 1;__float128 x=fabsq(a->r-(__float128)v[0])+fabsq(a->i-(__float128)v[1]);v[2]=x?nextafter((double)x,INFINITY):0;return !isfinite(v[2]);}
