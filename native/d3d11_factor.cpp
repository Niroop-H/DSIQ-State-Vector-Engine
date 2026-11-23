// Windows hardware-only FP64 factor evolution. Input: component widths, then
// (component, local target, local control mask, four row-major complex entries).
#include <windows.h>
#include <d3d11.h>
#include <d3dcompiler.h>
#include <dxgi.h>
#include <wrl/client.h>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using Microsoft::WRL::ComPtr;
static void check(HRESULT hr) { if (FAILED(hr)) throw std::runtime_error("Direct3D call failed: "+std::to_string(hr)); }
struct Complex { double re, im; };
struct Params { UINT offset, targetBit, controls, pairs; Complex matrix[4]; };
static_assert(sizeof(Params)==80);
static const char shader[] = R"(
cbuffer Params : register(b0) {
 uint offset, targetBit, controls, pairs;
 double2 m00, m01, m10, m11;
};
RWStructuredBuffer<double2> state : register(u0);
double2 product(double2 a, double2 b) {
 return double2(a.x*b.x-a.y*b.y, a.x*b.y+a.y*b.x);
}
[numthreads(64,1,1)]
void main(uint3 id : SV_DispatchThreadID) {
 uint j=id.x;
 if(j>=pairs)return;
 uint lo=j & (targetBit-1);
 uint x=lo+((j-lo)<<1);
 if((x&controls)!=controls)return;
 uint a=offset+x,b=a+targetBit;
 double2 v=state[a],w=state[b];
 state[a]=product(m00,v)+product(m01,w);
 state[b]=product(m10,v)+product(m11,w);
})";
int main() try {
 unsigned groups,gates;
 if(!(std::cin>>groups>>gates)||groups==0||groups>4096||gates>100000) return 2;
 std::vector<unsigned> sizes(groups),offsets(groups);
 unsigned total=0;
 for(unsigned i=0;i<groups;i++){
    unsigned width;
    if(!(std::cin>>width)||width==0||width>20)return 2;
    offsets[i]=total; sizes[i]=1u<<width; total+=sizes[i];
    if(total>(1u<<23))return 2;
 }
 ComPtr<IDXGIFactory1> factory; check(CreateDXGIFactory1(IID_PPV_ARGS(&factory)));
 ComPtr<ID3D11Device> device; ComPtr<ID3D11DeviceContext> context; DXGI_ADAPTER_DESC1 desc{};
 for(UINT i=0;;i++){
    ComPtr<IDXGIAdapter1> adapter;
    HRESULT hr=factory->EnumAdapters1(i,&adapter);
    if(hr==DXGI_ERROR_NOT_FOUND)throw std::runtime_error("No FP64 hardware adapter");
    check(hr);check(adapter->GetDesc1(&desc));
    if(desc.Flags & DXGI_ADAPTER_FLAG_SOFTWARE)continue;
    D3D_FEATURE_LEVEL fl;
    if(FAILED(D3D11CreateDevice(adapter.Get(),D3D_DRIVER_TYPE_UNKNOWN,nullptr,0,nullptr,0,
        D3D11_SDK_VERSION,device.ReleaseAndGetAddressOf(),&fl,context.ReleaseAndGetAddressOf())))continue;
    D3D11_FEATURE_DATA_DOUBLES fp{};
    if(fl>=D3D_FEATURE_LEVEL_11_0 && SUCCEEDED(device->CheckFeatureSupport(D3D11_FEATURE_DOUBLES,&fp,sizeof(fp))) && fp.DoublePrecisionFloatShaderOps)break;
 }
 ComPtr<ID3DBlob> code,errors;
 HRESULT hr=D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,nullptr,"main","cs_5_0",
                        D3DCOMPILE_IEEE_STRICTNESS,0,&code,&errors);
 if(FAILED(hr)&&errors)std::cerr<<static_cast<const char*>(errors->GetBufferPointer());
 check(hr);
 ComPtr<ID3D11ComputeShader> compute;
 check(device->CreateComputeShader(code->GetBufferPointer(),code->GetBufferSize(),nullptr,&compute));
 std::vector<Complex> initial(total);for(auto off:offsets)initial[off]={1,0};
 D3D11_BUFFER_DESC bd{};
 bd.ByteWidth=total*sizeof(Complex);bd.BindFlags=D3D11_BIND_UNORDERED_ACCESS;
 bd.MiscFlags=D3D11_RESOURCE_MISC_BUFFER_STRUCTURED;bd.StructureByteStride=sizeof(Complex);
 D3D11_SUBRESOURCE_DATA input{};input.pSysMem=initial.data();
 ComPtr<ID3D11Buffer> state,params,staging;
 check(device->CreateBuffer(&bd,&input,&state));
 D3D11_UNORDERED_ACCESS_VIEW_DESC ud{};ud.ViewDimension=D3D11_UAV_DIMENSION_BUFFER;ud.Buffer.NumElements=total;
 ComPtr<ID3D11UnorderedAccessView> uav;check(device->CreateUnorderedAccessView(state.Get(),&ud,&uav));
 bd={};bd.ByteWidth=sizeof(Params);bd.BindFlags=D3D11_BIND_CONSTANT_BUFFER;
 check(device->CreateBuffer(&bd,nullptr,&params));
 context->CSSetShader(compute.Get(),nullptr,0);context->CSSetConstantBuffers(0,1,params.GetAddressOf());
 context->CSSetUnorderedAccessViews(0,1,uav.GetAddressOf(),nullptr);
 for(unsigned i=0;i<gates;i++){
   unsigned group,target,mask;Params p{};
   if(!(std::cin>>group>>target>>mask)||group>=groups||target>=20)return 2;
   p.targetBit=1u<<target;p.offset=offsets[group];p.controls=mask;p.pairs=sizes[group]/2;
   if(p.targetBit>=sizes[group]||mask>=sizes[group]||(mask&p.targetBit))return 2;
   for(auto &z:p.matrix)if(!(std::cin>>z.re>>z.im)||!std::isfinite(z.re)||!std::isfinite(z.im))return 2;
   context->UpdateSubresource(params.Get(),0,nullptr,&p,0,0);
   context->Dispatch((p.pairs+63)/64,1,1);
 }
 bd={};bd.ByteWidth=total*sizeof(Complex);bd.Usage=D3D11_USAGE_STAGING;bd.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
 check(device->CreateBuffer(&bd,nullptr,&staging));
 context->CopyResource(staging.Get(),state.Get());D3D11_MAPPED_SUBRESOURCE mapped{};
 check(context->Map(staging.Get(),0,D3D11_MAP_READ,0,&mapped));
 auto out=static_cast<const Complex*>(mapped.pData);
 std::cout<<desc.VendorId<<' '<<desc.DeviceId<<' '<<gates<<' '<<total<<'\n'<<std::setprecision(17);
 std::wcerr<<desc.Description<<L'\n';
 for(unsigned i=0;i<total;i++){
    if(!std::isfinite(out[i].re)||!std::isfinite(out[i].im))throw std::runtime_error("Nonfinite GPU coefficient");
    std::cout<<out[i].re<<' '<<out[i].im<<'\n';
 }
 context->Unmap(staging.Get(),0);return 0;
} catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
