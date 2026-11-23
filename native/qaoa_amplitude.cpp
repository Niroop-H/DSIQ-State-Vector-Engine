// Two-layer uniform-angle ZZ/RX QAOA on an undirected, unweighted graph.
// Input: n m gamma0 beta0 gamma1 beta1 output_bitstring, then m edges u v.
// Angles are gate rotation angles. H on every wire prepares the initial state.
#include <algorithm>
#include <bit>
#include <cmath>
#include <complex>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

using Complex = std::complex<double>;
using Word = std::uint64_t;

struct Graph {
    unsigned n, m;
    double gamma[2], beta[2];
    Word output = 0;
    std::vector<Word> neighbors;

    explicit Graph(std::istream& in) {
        std::string bits;
        if (!(in >> n >> m >> gamma[0] >> beta[0] >> gamma[1] >> beta[1] >> bits)
            || n == 0 || n > 60 || m > n*(n-1)/2 || bits.size() != n)
            throw std::invalid_argument("Invalid circuit header");
        for (int k=0;k<2;++k)
            if (!std::isfinite(gamma[k]) || !std::isfinite(beta[k]))
                throw std::invalid_argument("Nonfinite angle");
        for (char ch:bits) {
            if (ch!='0' && ch!='1') throw std::invalid_argument("Invalid output bit");
            output = 2*output + (ch-'0');
        }
        neighbors.assign(n,0);
        for (unsigned e=0;e<m;++e) {
            unsigned u,v;
            if (!(in>>u>>v) || u>=n || v>=n || u==v || ((neighbors[u]>>v)&1))
                throw std::invalid_argument("Invalid or repeated edge");
            neighbors[u] |= Word{1}<<v;
            neighbors[v] |= Word{1}<<u;
        }
        std::string extra;
        if (in>>extra) throw std::invalid_argument("Unexpected trailing input");
    }

    template<class F> void walk_cuts(Word length, Word prefix, F visit) const {
        Word x=prefix;
        int cut=0;
        for (unsigned q=0;q<n;++q)
            if ((prefix>>q)&1) cut+=std::popcount(neighbors[q]&~prefix);
        for (Word i=0;;) {
            visit(x^prefix,cut);
            if (++i==length) break;
            unsigned q=std::countr_zero(i);
            int delta=std::popcount(neighbors[q])-2*std::popcount(neighbors[q]&x);
            cut+=((x>>q)&1)?-delta:delta;
            x^=Word{1}<<q;
        }
    }
};

std::vector<Complex> phases(unsigned m,double theta) {
    std::vector<Complex> power(m+1,1.), phase(m+1);
    Complex unit=std::polar(1.,theta/2);
    for (unsigned j=1;j<=m;++j) power[j]=power[j-1]*unit;
    for (unsigned j=0;j<=m;++j) {
        int k=2*int(j)-int(m);
        phase[j]=k<0?std::conj(power[-k]):power[k];
    }
    return phase;
}

Complex project(const Graph& graph, Word half) {
    const auto first=phases(graph.m,graph.gamma[0]);
    const double scale=std::exp2(-double(graph.n)/2);
    std::vector<Complex> state(half);
    graph.walk_cuts(half,0,[&](Word x,int cut){state[x]=scale*first[cut];});
    const double c=std::cos(graph.beta[0]/2), s=std::sin(graph.beta[0]/2);
    auto mix=[&](Word i, Word j) {
        const Complex a=state[i], b=state[j];
        state[i]=c*a+Complex(s*b.imag(),-s*b.real());
        state[j]=c*b+Complex(s*a.imag(),-s*a.real());
    };
    for (Word stride=1;stride<half;stride*=2)
        for (Word base=0;base<half;base+=2*stride)
            for (Word i=base;i<base+stride;++i) mix(i,i+stride);
    // Flipping the omitted (high) bit maps to the complement representative.
    if (half==1) state[0]*=Complex(c,-s);
    else for (Word i=0;i<half/2;++i) mix(i,half-1-i);

    const auto second=phases(graph.m,graph.gamma[1]);
    std::vector<Complex> same(graph.n+1,1.), different(graph.n+1,1.), weight(graph.n+1);
    for (unsigned i=1;i<=graph.n;++i) {
        same[i]=same[i-1]*std::cos(graph.beta[1]/2);
        different[i]=different[i-1]*Complex(0,-std::sin(graph.beta[1]/2));
    }
    for (unsigned d=0;d<=graph.n;++d)
        weight[d]=same[graph.n-d]*different[d]+same[d]*different[graph.n-d];
    // Fold both members of each complementary pair into the last mixer row.
    Complex sum=0, correction=0;
    graph.walk_cuts(half,0,[&](Word x,int cut) {
        unsigned distance=std::popcount(x^graph.output);
        Complex y=state[x]*second[cut]*weight[distance]-correction;
        Complex t=sum+y;
        correction=(t-sum)-y;
        sum=t;
    });
    return sum;
}

// Fix the high input bits before the first mixer and the high output
// bits after it. Only an array over the low bits is needed in each tile.
// The missing high-input half is included by projecting both output complements.
Complex tiled(const Graph& g,unsigned low,bool pilot,Word first_u,Word first_v) {
    const Word length=Word{1}<<low, high=Word{1}<<(g.n-low);
    if (first_u>=high/2 || first_v>=high) throw std::invalid_argument("Invalid tile coordinates");
    const auto phase0=phases(g.m,g.gamma[0]), phase1=phases(g.m,g.gamma[1]);
    auto weights=[](unsigned count,double angle) {
        std::vector<Complex> same(count+1,1.), flip(count+1,1.), w(count+1);
        for (unsigned i=1;i<=count;++i) {
            same[i]=same[i-1]*std::cos(angle/2);
            flip[i]=flip[i-1]*Complex(0,-std::sin(angle/2));
        }
        for (unsigned i=0;i<=count;++i) w[i]=same[count-i]*flip[i];
        return w;
    };
    const auto mixer=weights(g.n-low,g.beta[0]), final=weights(g.n,g.beta[1]);
    const double norm=std::exp2(-double(g.n)/2);
    const double c=std::cos(g.beta[0]/2), s=std::sin(g.beta[0]/2);
    std::vector<Complex> block(length);
    Complex sum=0, correction=0;
    for (Word u=first_u;u<(pilot?first_u+1:high/2);++u) {
        g.walk_cuts(length,u<<low,[&](Word x,int cut){block[x]=norm*phase0[cut];});
        for (Word step=1;step<length;step*=2)
            for (Word base=0;base<length;base+=2*step)
                for (Word i=base;i<base+step;++i) {
                    Complex a=block[i], b=block[i+step];
                    block[i]=c*a+Complex(s*b.imag(),-s*b.real());
                    block[i+step]=c*b+Complex(s*a.imag(),-s*a.real());
                }
        for (Word v=first_v;v<(pilot?first_v+1:high);++v) {
            Complex prefactor=mixer[std::popcount(u^v)];
            g.walk_cuts(length,v<<low,[&](Word x,int cut){
                unsigned d=std::popcount(((v<<low)|x)^g.output);
                Complex term=block[x]*phase1[cut]*prefactor*(final[d]+final[g.n-d]);
                Complex y=term-correction, t=sum+y;
                correction=(t-sum)-y; sum=t;
            });
        }
    }
    return sum;
}

Word natural(const char* input) {
    const std::string text(input);
    if (text.empty() || text.find_first_not_of("0123456789")!=std::string::npos)
        throw std::invalid_argument("Expected an unsigned decimal integer");
    return std::stoull(text);
}

int main(int argc,char** argv) {
    try {
        if(argc!=1 && argc!=2 && argc!=3 && argc!=5)
            throw std::invalid_argument("Usage: program [budget_MiB [low_bits [tile_u tile_v]]]");
        Word budget=argc>=2?natural(argv[1]):1024;
        Graph graph(std::cin);
        const Word low=argc>=3?natural(argv[2]):graph.n-1;
        if (low>=graph.n) throw std::invalid_argument("low_bits must be smaller than n");
        Word half=Word{1}<<low;
        Word required=half*sizeof(Complex);
        if (required/1048576+(required%1048576!=0)>budget) {
            std::cerr<<"Coefficient bytes required: "<<required<<'\n';
            return 2;
        }
        auto value=argc<3?project(graph,half):
            tiled(graph,static_cast<unsigned>(low),argc==5,argc==5?natural(argv[3]):0,argc==5?natural(argv[4]):0);
        if (!std::isfinite(value.real()) || !std::isfinite(value.imag()))
            throw std::runtime_error("Nonfinite amplitude");
        if(argc==5) std::cout<<"partial_tile ";
        std::cout<<std::setprecision(17)<<value.real()<<' '<<value.imag()<<'\n';
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<e.what()<<'\n'; return 2;
    }
}
