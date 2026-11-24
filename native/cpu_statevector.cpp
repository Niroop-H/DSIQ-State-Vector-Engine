// FP64 selected amplitudes. Start from a product of local states, materialize
// dense coefficients on first nontrivial controlled operation. Wire 0 is LSB.
#include <algorithm>
#include <array>
#include <cstdint>
#include <map>
#include <optional>
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
    using Index = std::uint64_t;
    static constexpr unsigned max_qubits = 24;
    static_assert(max_qubits < 32 && 2 * max_qubits <= 64);
    static Index dimension(unsigned n) {
        if (!n || n > max_qubits) throw std::length_error("Unsupported width");
        return Index{1} << n;
    }
    Index length;
    enum class Basis { Zero, One, Unknown };
    std::vector<Basis> basis;
    std::vector<Pair> local;
    std::vector<Z> dense;
    void expand() {
        if (length > dense.max_size()) throw std::length_error("Dense allocation exceeds addressable storage");
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
    explicit State(unsigned n):length(dimension(n)),basis(n,Basis::Zero),local(n,Pair{1.,0.}) {}
    void apply(const Gate& g) {
        const unsigned target=1u<<g.q;
        if(dense.empty() && g.op==Op::Swap) {
            std::swap(basis[g.q],basis[std::countr_zero(g.mask)]);
            std::swap(local[g.q],local[std::countr_zero(g.mask)]);
            return;
        }
        if(dense.empty()) {
            unsigned uncertain=0;
            for(unsigned mask=g.mask;mask;mask&=mask-1) {
                const auto control=basis[std::countr_zero(mask)];
                if(control==Basis::Zero) return;
                if(control==Basis::Unknown) uncertain|=mask&-mask;
            }
            if(!uncertain) {
                auto& b=basis[g.q];
                if(g.op==Op::X && b!=Basis::Unknown) b=(b==Basis::Zero ? Basis::One : Basis::Zero);
                else if(g.op==Op::H || ((g.op==Op::RX || g.op==Op::RY) && g.angle!=0)) b=Basis::Unknown;
                transform(local[g.q][0],local[g.q][1],matrix(g)); return;
            }
            if(g.op==Op::Phase && basis[g.q]==Basis::Zero) return;
            if(g.op==Op::Phase && basis[g.q]==Basis::One && std::has_single_bit(uncertain)) {
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
    void apply_zz_layer(const std::vector<unsigned>& neighbors,unsigned edges,double angle) {
        if(dense.empty())expand();
        // All rotations in this layer commute. Their phase depends only on
        // the number of equal and unequal bit pairs, including global phase.
        const Z unit=std::polar(1.,angle/2);
        std::vector<Z> powers(edges+1,1.), phases(edges+1);
        for(unsigned i=1;i<=edges;++i)powers[i]=powers[i-1]*unit;
        for(unsigned i=0;i<=edges;++i) {
            int power=2*int(i)-int(edges);
            phases[i]=power<0?std::conj(powers[-power]):powers[power];
        }
        unsigned x=0;
        int cut=0;
        for(unsigned i=0;;) {
            dense[x]*=phases[cut];
            if(++i==length)break;
            unsigned q=std::countr_zero(i);
            int delta=std::popcount(neighbors[q])-2*std::popcount(x&neighbors[q]);
            cut+=((x>>q)&1)?-delta:delta;
            x^=1u<<q;
        }
    }
    Z amplitude(Index i) const {
        if(i>=length)throw std::invalid_argument("Invalid basis index");
        if(!dense.empty())return dense[i];
        Z value=1.;
        for(const auto& p:local) {value*=p[i&1];i>>=1;}
        return value;
    }
};
bool zz_at(const std::vector<Gate>& stream,size_t i) {
    if(stream.size()-i<3)return false;
    const Gate &a=stream[i],&b=stream[i+1],&c=stream[i+2];
    return a.op==Op::X && std::has_single_bit(a.mask) && b.op==Op::RZ &&
           c.op==Op::X && a.q==b.q && a.q==c.q && a.mask==c.mask;
}
void evolve(State& state,const std::vector<Gate>& stream,unsigned n) {
    for(size_t i=0;i<stream.size();) {
        if(!zz_at(stream,i)) {state.apply(stream[i++]);continue;}
        const size_t begin=i;
        const double angle=stream[i+1].angle;
        std::vector<unsigned> neighbors(n);
        while(zz_at(stream,i) && stream[i+1].angle==angle) {
            const auto& gate=stream[i];
            if(neighbors[gate.q]&gate.mask)break;
            neighbors[gate.q]|=gate.mask;
            neighbors[std::countr_zero(gate.mask)]|=1u<<gate.q;
            i+=3;
        }
        if(i-begin>=6)state.apply_zz_layer(neighbors,(i-begin)/3,angle);
        else for(size_t j=begin;j<i;++j)state.apply(stream[j]);
    }
}
// A real linear combination of products of |0>, |1>, |+>, and |->.
// A controlled X is I - 2P, with P projecting its controls onto |1>
// and its target onto |->. Each projection produces at most one new product.
// No nonzero term is discarded. If the term budget is exceeded the caller
// replays the original gates using the product-to-dense executor.
using Key=std::uint64_t;
using Terms=std::map<Key,long double>;
unsigned symbol(Key key,unsigned q) {return (key>>(2*q))&3u;}
Key replace_symbol(Key key,unsigned q,unsigned value) {
    return key^(Key(symbol(key,q)^value)<<(2*q));
}
long double overlap_weight(unsigned halves) {
    return std::ldexp((halves&1)?std::sqrt(0.5L):1.L,-int(halves/2));
}
void add_term(Terms& dest,Key key,long double weight) {
    auto [it,inserted]=dest.try_emplace(key,weight);
    if(!inserted) {
        it->second+=weight;
        if(it->second==0)dest.erase(it);
    }
}
void product_gate(Terms& next,Key key,long double weight,const Gate& g) {
    const unsigned target=symbol(key,g.q);
    if(g.op==Op::H) {add_term(next,replace_symbol(key,g.q,target^2),weight);return;}
    if(g.op==Op::Swap) {
        const unsigned c=std::countr_zero(g.mask);
        add_term(next,replace_symbol(replace_symbol(key,g.q,symbol(key,c)),c,target),weight);
        return;
    }
    if(target==2){add_term(next,key,weight);return;}
    Key projected=replace_symbol(key,g.q,3);
    unsigned uncertain=0;
    int sign=1;
    for(unsigned mask=g.mask;mask;mask&=mask-1) {
        const unsigned c=std::countr_zero(mask),v=symbol(key,c);
        if(v==0){add_term(next,key,weight);return;}
        if(v>=2) {
            ++uncertain;
            if(v==3)sign=-sign;
            projected=replace_symbol(projected,c,1);
        }
    }
    if(!uncertain) {
        add_term(next,target<2?replace_symbol(key,g.q,target^1):key,target==3?-weight:weight);
        return;
    }
    add_term(next,key,weight);
    if(target==1)sign=-sign;
    add_term(next,projected,-2*sign*weight*overlap_weight(uncertain+(target<2)));
}
std::optional<Terms> evolve_products(const std::vector<Gate>& stream) {
    if(!std::all_of(stream.begin(),stream.end(),[](const Gate& g) {
        return g.op==Op::H || g.op==Op::X || g.op==Op::Swap;
    }))return std::nullopt;
    Terms terms={{0,1}};
    for(const Gate& g:stream) {
        Terms next;
        for(const auto& [key,weight]:terms)product_gate(next,key,weight,g);
        if(next.size()>128)return std::nullopt;
        // Large cancelling coefficients make this representation ill-conditioned.
        // Recompute in the dense basis instead of pruning or rescaling terms.
        long double magnitude=0;
        for(const auto& term:next)magnitude+=std::abs(term.second);
        if(!std::isfinite(magnitude) || magnitude>16)return std::nullopt;
        terms.swap(next);
    }
    return terms;
}
double product_amplitude(const Terms& terms,unsigned n,unsigned index) {
    long double sum=0,compensation=0;
    for(const auto& [key,weight]:terms) {
        unsigned halves=0;
        int sign=1;
        for(unsigned q=0;q<n;++q) {
            const unsigned bit=(index>>q)&1,v=symbol(key,q);
            if(v<2 && v!=bit){sign=0;break;}
            if(v>=2)++halves;
            if(v==3 && bit)sign=-sign;
        }
        const long double y=sign*weight*overlap_weight(halves)-compensation;
        const long double updated=sum+y;
        compensation=(updated-sum)-y; sum=updated;
    }
    return static_cast<double>(sum);
}
int main() {
    try {
        std::ios::sync_with_stdio(false); std::cin.tie(nullptr);
        unsigned n,gates,probes;
        if(!(std::cin>>n>>gates>>probes)||n<1||n>24||gates>1000000||!probes)return 2;
        const auto start=std::chrono::steady_clock::now();
        State state(n);
        std::vector<Gate> stream;
        stream.reserve(gates);
        for(unsigned i=0;i<gates;++i)stream.push_back(read_gate(n));
        const auto products=evolve_products(stream);
        if(!products)evolve(state,stream,n);
        std::vector<Z> values;
        for(unsigned j=0;j<probes;++j) {
            std::uint64_t i;
            if(!(std::cin>>i))return 2;
            if(i>=(std::uint64_t{1}<<n))return 2;
            values.push_back(products?Z(product_amplitude(*products,n,i)):state.amplitude(i));
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
