/* MAH Quantum DSIQ native research kernel: fixed coefficient arena, FP64.
 * Input is a sequence of DSIQ1 programs; static factor partition from caller.
 * No disk scratch, simulator library, network dependency, or amplitude pruning.
 * The 4 MiB ceiling is for coefficient storage, not total process RSS.
 */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <errno.h>
#include <sys/resource.h>
#ifdef __linux__
#include <sys/socket.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <linux/audit.h>
#include <stddef.h>
#endif
#define NMAX 4096
#define CAP 262144u
#define PI 3.141592653589793238462643383279502884
#define FAIL(s) do {fprintf(stderr,"DSIQ: %s\n",s);exit(2);} while(0)
typedef struct { double r,i; } C;
typedef struct {unsigned off,size,w;} Group;
static C arena[CAP];
static Group grp[NMAX];
static int owner[NMAX], local[NMAX];
static char query[NMAX+1];
static C add(C a,C b){return (C){a.r+b.r,a.i+b.i};}
static C mul(C a,C b){return (C){a.r*b.r-a.i*b.i,a.r*b.i+a.i*b.r};}
static C cis(double t){return (C){cos(t),sin(t)};}
static double mag2(C a){return a.r*a.r+a.i*a.i;}
static int offgrid=-1;
#ifdef __linux__
/* Reject initiation of network sockets at the syscall boundary. Not a sandbox
 * for untrusted native code; only an explicit no-network guard for this CLI. */
static int disable_sockets(void){
 struct sock_filter f[]={BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,nr)),
 BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,__NR_socket,0,1),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EPERM),
 BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,__NR_socketpair,0,1),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EPERM),
 BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,__NR_connect,0,1),BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EPERM),
 BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW)};
 struct sock_fprog p={(unsigned short)(sizeof f/sizeof f[0]),f};
 if(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0)||prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER,&p))return 0;
 int fd=socket(AF_INET,SOCK_STREAM,0);return fd<0&&errno==EPERM;
}
#endif
static void metrics(unsigned *rss,unsigned *hwm,unsigned *swap){*rss=*hwm=*swap=0;
#ifdef __linux__
 FILE *f=fopen("/proc/self/status","r");if(!f)return;char line[256];while(fgets(line,sizeof line,f)){unsigned a;if(sscanf(line,"VmRSS: %u kB",&a)==1)*rss=a;if(sscanf(line,"VmHWM: %u kB",&a)==1)*hwm=a;if(sscanf(line,"VmSwap: %u kB",&a)==1)*swap=a;}fclose(f);
#endif
}
/* Matrix by gate name. Control counts are validated separately. */
static void matrix(const char *name,double t,double p,double l,C M[4]){C z={0,0},o={1,0},i={0,1};double c=cos(t/2),s=sin(t/2),h=sqrt(.5);M[0]=M[3]=o;M[1]=M[2]=z;
 if(!strcmp(name,"i"))return;
 if(!strcmp(name,"h")){M[0]=M[1]=M[2]=(C){h,0};M[3]=(C){-h,0};}
 else if(!strcmp(name,"x")||!strcmp(name,"cx")||!strcmp(name,"ccx")||!strcmp(name,"mcx")){M[0]=M[3]=z;M[1]=M[2]=o;}
 else if(!strcmp(name,"y")||!strcmp(name,"cy")){M[0]=M[3]=z;M[1]=(C){0,-1};M[2]=i;}
 else if(!strcmp(name,"z")||!strcmp(name,"cz"))M[3]=(C){-1,0};
 else if(!strcmp(name,"s"))M[3]=i;else if(!strcmp(name,"sdg"))M[3]=(C){0,-1};
 else if(!strcmp(name,"t"))M[3]=cis(PI/4);else if(!strcmp(name,"tdg"))M[3]=cis(-PI/4);
 else if(!strcmp(name,"rx")||!strcmp(name,"crx")){M[0]=M[3]=(C){c,0};M[1]=M[2]=(C){0,-s};}
 else if(!strcmp(name,"ry")||!strcmp(name,"cry")){M[0]=M[3]=(C){c,0};M[1]=(C){-s,0};M[2]=(C){s,0};}
 else if(!strcmp(name,"rz")||!strcmp(name,"crz")){M[0]=cis(-t/2);M[3]=cis(t/2);}
 else if(!strcmp(name,"p")||!strcmp(name,"cp"))M[3]=cis(t);
 else if(!strcmp(name,"u")||!strcmp(name,"cu")){M[0]=(C){c,0};M[1]=mul((C){-s,0},cis(l));M[2]=mul((C){s,0},cis(p));M[3]=mul((C){c,0},mul(cis(p),cis(l)));}
 else if(!strcmp(name,"sx")||!strcmp(name,"csx")){M[0]=M[3]=(C){.5,.5};M[1]=M[2]=(C){.5,-.5};}
 else if(!strcmp(name,"sy")){M[0]=M[3]=M[2]=(C){.5,.5};M[1]=(C){-.5,-.5};}
 else FAIL("unsupported gate");
}
static int expected(const char *s,int k){if(!strcmp(s,"mcx"))return k>0?k:-1;if(!strcmp(s,"ccx"))return 2;if(!strcmp(s,"cx")||!strcmp(s,"cy")||!strcmp(s,"cz")||!strcmp(s,"crx")||!strcmp(s,"cry")||!strcmp(s,"crz")||!strcmp(s,"cp")||!strcmp(s,"cu")||!strcmp(s,"csx")||!strcmp(s,"swap"))return 1;return 0;}
static void execute(int n){int groups;unsigned used=0;if(scanf("%d",&groups)!=1||groups<1||groups>n)FAIL("invalid group count");for(int q=0;q<n;q++)owner[q]=-1;for(int g=0;g<groups;g++){int w;if(scanf("%d",&w)!=1||w<1||w>18)FAIL("group exceeds bounded workspace");unsigned size=1u<<w;if(size>CAP-used)FAIL("coefficient arena exhausted before execution");grp[g]=(Group){used,size,(unsigned)w};for(int j=0;j<w;j++){int q;if(scanf("%d",&q)!=1||q<0||q>=n||owner[q]!=-1)FAIL("invalid wire mapping");owner[q]=g;local[q]=j;}memset(arena+used,0,size*sizeof(C));arena[used]=(C){1,0};used+=size;}for(int q=0;q<n;q++)if(owner[q]<0)FAIL("incomplete wire mapping");
 unsigned count;if(scanf("%u",&count)!=1||count>10000000)FAIL("invalid operation count");for(unsigned k=0;k<count;k++){char name[16];int q,cs;double t,p,l;if(scanf("%15s%d%d",name,&q,&cs)!=3||q<0||q>=n||cs<0||cs>=n||expected(name,cs)!=cs)FAIL("invalid gate signature");Group g=grp[owner[q]];unsigned bit=1u<<local[q],control=0;for(int j=0;j<cs;j++){int a;if(scanf("%d",&a)!=1||a<0||a>=n||a==q||owner[a]!=owner[q])FAIL("gate crosses planned factor");unsigned b=1u<<local[a];if(control&b)FAIL("duplicate control");control|=b;}if(scanf("%lf%lf%lf",&t,&p,&l)!=3||!isfinite(t)||!isfinite(p)||!isfinite(l))FAIL("nonfinite gate parameter");C *A=arena+g.off;if(!strcmp(name,"swap")){for(unsigned x=0;x<g.size;x++)if((x&bit)&&!(x&control)){unsigned y=x^bit^control;C temp=A[x];A[x]=A[y];A[y]=temp;}continue;}C M[4];matrix(name,t,p,l,M);for(unsigned x=0;x<g.size;x++)if(!(x&bit)&&(x&control)==control){unsigned y=x|bit;C a=A[x],b=A[y];A[x]=add(mul(M[0],a),mul(M[1],b));A[y]=add(mul(M[2],a),mul(M[3],b));if(!isfinite(A[x].r)||!isfinite(A[x].i)||!isfinite(A[y].r)||!isfinite(A[y].i))FAIL("nonfinite amplitude");}}
 double norm=1;for(int g=0;g<groups;g++){double s=0;for(unsigned j=0;j<grp[g].size;j++)s+=mag2(arena[grp[g].off+j]);norm*=s;}unsigned queries;if(scanf("%u",&queries)!=1||queries>1000000)FAIL("invalid query count");for(unsigned k=0;k<queries;k++){if(scanf("%4096s",query)!=1||strlen(query)!=(size_t)n)FAIL("invalid query width");unsigned ix[NMAX]={0};for(int q=0;q<n;q++){char b=query[n-1-q];if(b!='0'&&b!='1')FAIL("invalid query");if(b=='1')ix[owner[q]]|=1u<<local[q];}double log=0;C u={1,0};int zero=0;for(int g=0;g<groups;g++){C a=arena[grp[g].off+ix[g]];double m=hypot(a.r,a.i);if(m==0){zero=1;break;}log+=log2(m);u=mul(u,(C){a.r/m,a.i/m});}if(zero)printf("{\"real\":0,\"imag\":0,\"log2Magnitude\":null}\n");else printf("{\"real\":%.17g,\"imag\":%.17g,\"log2Magnitude\":%.17g}\n",u.r*exp2(log),u.i*exp2(log),log);}
 unsigned rss,hwm,swap;metrics(&rss,&hwm,&swap);printf("{\"qubits\":%d,\"gates\":%u,\"factors\":%d,\"coefficientBytes\":%zu,\"arenaBytes\":%zu,\"norm\":%.17g,\"rssKiB\":%u,\"hwmKiB\":%u,\"swapKiB\":%u,\"socketDenied\":%d}\n",n,count,groups,(size_t)used*sizeof(C),sizeof arena,norm,rss,hwm,swap,offgrid);}
int main(void){
#ifdef __linux__
 offgrid=disable_sockets();if(!offgrid)FAIL("network deny guard unavailable");
#endif
 char hdr[16];int n;while(scanf("%15s",hdr)==1){if(strcmp(hdr,"DSIQ1")||scanf("%d",&n)!=1||n<1||n>NMAX)FAIL("invalid program header");execute(n);}return 0;}
