// FP64 selected amplitudes. Start from a product of local states, materialize
// dense coefficients on first nontrivial controlled operation. Wire 0 is LSB.
#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cmath>
#include <complex>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using Z = std::complex<double>;
using Pair = std::array<Z,2>;
using Matrix = std::array<Z,4>;

enum class Op { H, X, RX, RY, RZ, Phase, Swap };
struct Gate { Op op; unsigned q, mask; double angle; };
Gate read_gate(unsigned n) {
    std::string name;
    unsigned q,k;
    double angle;
    if (!(std::cin >> name >> q >> angle >> k) || q>=n || k>=n || !std::isfinite(angle))
        throw std::invalid_argument("Invalid gate");
    unsigned mask=0;
    for(unsigned i=0;i<k;++i) {
        unsigned c;
        if (!(std::cin>>c) || c>=n || c==q || (mask&(1u<<c)))
            throw std::invalid_argument("Invalid controls");
        mask|=1u<<c;
    }
    Op op;
    if(name=="h" && !k) op=Op::H;
    else if ((name=="x" && !k) || (name=="cx" && k==1) || (name=="mcx" && k)) op=Op::X;
    else if(name=="rx" && !k) op=Op::RX;
    else if(name=="ry" && !k) op=Op::RY;
    else if(name=="rz" && !k) op=Op::RZ;
    else if((name=="p" && !k) || (name=="cp" && k==1)) op=Op::Phase;
    else if(name=="swap" && k==1) op=Op::Swap;
    else throw std::invalid_argument("Unsupported gate or arity: "+name);
    return {op,q,mask,angle};
}
Matrix matrix(const Gate& g) {
    constexpr double h=0.707106781186547524400844362104849;
    if(g.op==Op::H) return {h,h,h,-h};
    if(g.op==Op::X) return {0.,1.,1.,0.};
    if(g.op==Op::Phase) return {1.,0.,0.,std::polar(1.,g.angle)};
    const double c=std::cos(g.angle/2), s=std::sin(g.angle/2);
    if(g.op==Op::RX) return {c,Z(0,-s),Z(0,-s),c};
    if(g.op==Op::RY) return {c,-s,s,c};
    return {Z(c,-s),0.,0.,Z(c,s)};
}
void transform(Z& a,Z& b,const Matrix& m) {
    Z x=a, y=b;
    a=m[0]*x+m[1]*y; b=m[2]*x+m[3]*y;
}
class State {
    unsigned length;
    std::vector<Pair> local;
    std::vector<Z> dense;
    void expand() {
        dense.resize(length);
        dense[0]=1;
        unsigned stride=1;
        for(const auto& p:local) {
            for(unsigned i=0;i<stride;++i) {
                dense[i+stride]=dense[i]*p[1];
                dense[i]*=p[0];
            }
            stride*=2;
        }
    }
public:
    explicit State(unsigned n):length(1u<<n),local(n,Pair{1.,0.}) {}
    void apply(const Gate& g) {
        const unsigned target=1u<<g.q;
        if(dense.empty() && g.op==Op::Swap) {
            std::swap(local[g.q],local[std::countr_zero(g.mask)]);
            return;
        }
        if(dense.empty()) {
            unsigned uncertain=0;
            for(unsigned mask=g.mask;mask;mask&=mask-1) {
                const auto& p=local[std::countr_zero(mask)];
                if(p[1]==Z{}) return;
                if(p[0]!=Z{}) uncertain|=mask&-mask;
            }
            if(!uncertain) {
                transform(local[g.q][0],local[g.q][1],matrix(g)); return;
            }
            if(g.op==Op::Phase && local[g.q][1]==Z{}) return;
            if(g.op==Op::Phase && local[g.q][0]==Z{} && std::has_single_bit(uncertain)) {
                local[std::countr_zero(uncertain)][1]*=std::polar(1.,g.angle); return;
            }
            expand();
        }
        const Matrix m=matrix(g);
        // Enumerate free bits only. For SWAP these pairs have control=1,target=0.
        if(g.mask) {
            unsigned free=(length-1)^(g.mask|target);
            for(unsigned part=free;;part=(part-1)&free) {
                unsigned i=g.mask|part;
                if(g.op==Op::Swap) std::swap(dense[i],dense[i^target^g.mask]);
                else if(g.op==Op::X) std::swap(dense[i],dense[i|target]);
                else dense[i|target]*=m[3];
                if(!part) break;
            }
            return;
        }
        for(unsigned base=0;base<length;base+=2*target)
            for(unsigned i=base;i<base+target;++i)
                transform(dense[i],dense[i+target],m);
    }
    Z amplitude(unsigned i) const {
        if(i>=length)throw std::invalid_argument("Invalid basis index");
        if(!dense.empty())return dense[i];
        Z value=1.;
        for(const auto& p:local) {value*=p[i&1];i>>=1;}
        return value;
    }
};
int main() {
    try {
        std::ios::sync_with_stdio(false); std::cin.tie(nullptr);
        unsigned n,gates,probes;
        if(!(std::cin>>n>>gates>>probes)||n<1||n>24||!probes)return 2;
        const auto start=std::chrono::steady_clock::now();
        State state(n);
        for(unsigned i=0;i<gates;++i)state.apply(read_gate(n));
        std::vector<Z> values;
        for(unsigned j=0;j<probes;++j) {
            unsigned i;
            if(!(std::cin>>i))return 2;
            values.push_back(state.amplitude(i));
        }
        double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        std::cout<<std::setprecision(17)<<"{\"ms\":"<<ms<<",\"values\":[";
        for(unsigned i=0;i<values.size();++i) {
            if(i)std::cout<<',';
            std::cout<<'['<<values[i].real()<<','<<values[i].imag()<<']';
        }
        std::cout<<"]}\n";
    } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
