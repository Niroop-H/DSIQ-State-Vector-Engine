/* MAH Quantum DSIQ: native parallel evolution of disjoint exact components.
 * Shares the serial numerical arithmetic. A component has one writer, and
 * gates within it retain source order. No MPI, GPU, or connected-state split.
 * The 4 MiB cap covers coefficients; queue metadata and stacks are separate.
 */
#define main dsiq_serial_main
#include "dsiq_factor.c"
#undef main
#include <pthread.h>
#include <stdatomic.h>
#include <time.h>
#define NONE UINT32_MAX
#define MAX_OPS 100000u
#define MAX_THREADS 128
#define STACK_BYTES (128u*1024u)
typedef struct {unsigned bit,control,next;int swap;C m[4];} Op;
typedef struct {const Op *ops;unsigned first[NMAX];unsigned groups;atomic_uint next;} Job;
static void apply_op(Group g,const Op *o){C *a=arena+g.off;unsigned bit=o->bit,control=o->control;
 if(o->swap){for(unsigned x=0;x<g.size;x++)if((x&bit)&&!(x&control)){unsigned y=x^bit^control;C z=a[x];a[x]=a[y];a[y]=z;}return;}
 for(unsigned x=0;x<g.size;x++)if(!(x&bit)&&(x&control)==control){unsigned y=x|bit;C u=a[x],v=a[y];a[x]=add(mul(o->m[0],u),mul(o->m[1],v));a[y]=add(mul(o->m[2],u),mul(o->m[3],v));if(!isfinite(a[x].r)||!isfinite(a[x].i)||!isfinite(a[y].r)||!isfinite(a[y].i))FAIL("nonfinite parallel amplitude");}}
static void *work(void *arg){Job *j=arg;unsigned g;while((g=atomic_fetch_add_explicit(&j->next,1,memory_order_relaxed))<j->groups){for(unsigned k=j->first[g];k!=NONE;k=j->ops[k].next)apply_op(grp[g],&j->ops[k]);}return NULL;}
static uint64_t nanos(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))FAIL("monotonic clock unavailable");return (uint64_t)t.tv_sec*1000000000u+(uint64_t)t.tv_nsec;}
static void execute_parallel(int n,unsigned threads){int groups;unsigned used=0;if(scanf("%d",&groups)!=1||groups<1||groups>n)FAIL("invalid group count");for(int q=0;q<n;q++)owner[q]=-1;
 for(int g=0;g<groups;g++){int w;if(scanf("%d",&w)!=1||w<1||w>18)FAIL("group exceeds bounded workspace");unsigned size=1u<<w;if(size>CAP-used)FAIL("coefficient arena exhausted before execution");grp[g]=(Group){used,size,(unsigned)w};for(int j=0;j<w;j++){int q;if(scanf("%d",&q)!=1||q<0||q>=n||owner[q]!=-1)FAIL("invalid wire mapping");owner[q]=g;local[q]=j;}memset(arena+used,0,size*sizeof(C));arena[used]=(C){1,0};used+=size;}for(int q=0;q<n;q++)if(owner[q]<0)FAIL("incomplete wire mapping");
 unsigned count;if(scanf("%u",&count)!=1||count>MAX_OPS)FAIL("operation queue limit exceeded");Op *ops=calloc(count?count:1,sizeof(Op));if(!ops)FAIL("operation queue allocation failed");Job job={.ops=ops,.groups=(unsigned)groups,.next=ATOMIC_VAR_INIT(0)};unsigned last[NMAX];for(int g=0;g<groups;g++)job.first[g]=last[g]=NONE;
 for(unsigned k=0;k<count;k++){char name[16];int q,cs;double t,p,l;if(scanf("%15s%d%d",name,&q,&cs)!=3||q<0||q>=n||cs<0||cs>=n||expected(name,cs)!=cs)FAIL("invalid gate signature");unsigned bit=1u<<local[q],control=0;for(int j=0;j<cs;j++){int a;if(scanf("%d",&a)!=1||a<0||a>=n||a==q||owner[a]!=owner[q])FAIL("gate crosses planned factor");unsigned b=1u<<local[a];if(control&b)FAIL("duplicate control");control|=b;}if(scanf("%lf%lf%lf",&t,&p,&l)!=3||!isfinite(t)||!isfinite(p)||!isfinite(l))FAIL("nonfinite gate parameter");Op *o=&ops[k];o->bit=bit;o->control=control;o->next=NONE;o->swap=!strcmp(name,"swap");if(!o->swap)matrix(name,t,p,l,o->m);int g=owner[q];if(job.first[g]==NONE)job.first[g]=k;else ops[last[g]].next=k;last[g]=k;}
 uint64_t start=nanos();if(threads==1)work(&job);else{pthread_attr_t attr;pthread_t ids[MAX_THREADS];if(pthread_attr_init(&attr)||pthread_attr_setstacksize(&attr,STACK_BYTES))FAIL("thread stack setup failed");for(unsigned i=0;i<threads;i++)if(pthread_create(&ids[i],&attr,work,&job))FAIL("worker creation failed");for(unsigned i=0;i<threads;i++)if(pthread_join(ids[i],NULL))FAIL("worker join failed");pthread_attr_destroy(&attr);}uint64_t elapsed=nanos()-start;
 double norm=1;for(int g=0;g<groups;g++){double s=0;for(unsigned j=0;j<grp[g].size;j++)s+=mag2(arena[grp[g].off+j]);norm*=s;}
 unsigned queries;if(scanf("%u",&queries)!=1||queries>1000000)FAIL("invalid query count");for(unsigned k=0;k<queries;k++){if(scanf("%4096s",query)!=1||strlen(query)!=(size_t)n)FAIL("invalid query width");unsigned ix[NMAX]={0};for(int q=0;q<n;q++){char b=query[n-1-q];if(b!='0'&&b!='1')FAIL("invalid query");if(b=='1')ix[owner[q]]|=1u<<local[q];}double log=0;C u={1,0};int zero=0;for(int g=0;g<groups;g++){C a=arena[grp[g].off+ix[g]];double m=hypot(a.r,a.i);if(m==0){zero=1;break;}log+=log2(m);u=mul(u,(C){a.r/m,a.i/m});}if(zero)printf("{\"real\":0,\"imag\":0,\"log2Magnitude\":null}\n");else printf("{\"real\":%.17g,\"imag\":%.17g,\"log2Magnitude\":%.17g}\n",u.r*exp2(log),u.i*exp2(log),log);}
 // Serialize all binary64 coefficient bits (hex floats are exact and portable).
 for(int g=0;g<groups;g++){printf("{\"component\":%d,\"coefficients\":[",g);for(unsigned j=0;j<grp[g].size;j++){C a=arena[grp[g].off+j];printf("%s[\"%a\",\"%a\"]",j?",":"",a.r,a.i);}puts("]}");}
 unsigned rss,hwm,swap;metrics(&rss,&hwm,&swap);printf("{\"qubits\":%d,\"gates\":%u,\"threads\":%u,\"factors\":%d,\"coefficientBytes\":%zu,\"arenaBytes\":%zu,\"operationMetadataBytes\":%zu,\"threadStackLimitBytes\":%zu,\"norm\":%.17g,\"executionNanos\":%llu,\"rssKiB\":%u,\"hwmKiB\":%u,\"swapKiB\":%u,\"socketDenied\":%d}\n",n,count,threads,groups,(size_t)used*sizeof(C),sizeof arena,(size_t)(count?count:1)*sizeof(Op),threads>1?(size_t)threads*STACK_BYTES:0,norm,(unsigned long long)elapsed,rss,hwm,swap,offgrid);free(ops);}
int main(int argc,char **argv){if(argc!=2)FAIL("usage: dsiq-parallel THREADS");char *end;errno=0;long threads=strtol(argv[1],&end,10);if(errno||*end||threads<1||threads>MAX_THREADS)FAIL("invalid thread count");
#ifdef __linux__
 offgrid=disable_sockets();if(!offgrid)FAIL("network deny guard unavailable");
#endif
 char hdr[16];int n;while(scanf("%15s",hdr)==1){if(strcmp(hdr,"DSIQ1")||scanf("%d",&n)!=1||n<1||n>NMAX)FAIL("invalid program header");execute_parallel(n,(unsigned)threads);}return 0;}
