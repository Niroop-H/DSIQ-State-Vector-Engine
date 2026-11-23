#include "QuEST.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
int main(void){
 int n,ng,np;
 if(scanf("%d%d%d",&n,&ng,&np)!=3||n<1||n>24||ng<0||np<1)return 2;
 double start=now();
 QuESTEnv env=createQuESTEnv();
 Qureg reg=createQureg(n,env);initZeroState(reg);
 for(int j=0;j<ng;j++){
  char name[16];int q,k,c[24];double a;
  if(scanf("%15s%d%lf%d",name,&q,&a,&k)!=4||k<0||k>=n)return 2;
  for(int i=0;i<k;i++)if(scanf("%d",&c[i])!=1)return 2;
  if(!strcmp(name,"h"))hadamard(reg,q);
  else if(!strcmp(name,"x"))pauliX(reg,q);
  else if(!strcmp(name,"cx"))controlledNot(reg,c[0],q);
  else if(!strcmp(name,"mcx")){
   ComplexMatrix2 x={.real={{0,1},{1,0}}};multiControlledUnitary(reg,c,k,q,x);
  }
  else if(!strcmp(name,"p"))phaseShift(reg,q,a);
  else if(!strcmp(name,"cp"))controlledPhaseShift(reg,c[0],q,a);
  else if(!strcmp(name,"rx"))rotateX(reg,q,a);
  else if(!strcmp(name,"ry"))rotateY(reg,q,a);
  else if(!strcmp(name,"rz"))rotateZ(reg,q,a);
  else if(!strcmp(name,"swap"))swapGate(reg,c[0],q);
  else return 3;
 }
 Complex *v=calloc(np,sizeof *v);
 for(int i=0;i<np;i++){int idx;if(scanf("%d",&idx)!=1)return 2;v[i]=getAmp(reg,idx);}
 double ms=1000*(now()-start);
 printf("{\"ms\":%.10g,\"values\":[",ms);
 for(int i=0;i<np;i++)printf("%s[%.17g,%.17g]",i?",":"",v[i].real,v[i].imag);
 puts("]}");free(v);destroyQureg(reg,env);destroyQuESTEnv(env);return 0;
}
