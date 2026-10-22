// oneDPL host algorithms with the TBB backend, built with a non-SYCL compiler.
#include <oneapi/dpl/algorithm>
#include <oneapi/dpl/execution>
#include <oneapi/dpl/numeric>

#include <iostream>
#include <vector>

int main() {
    std::vector<long> v(100000);
    for (long i = 0; i < static_cast<long>(v.size()); ++i) {
        v[i] = v.size() - i;
    }

    oneapi::dpl::sort(oneapi::dpl::execution::par, v.begin(), v.end());
    const long sum = oneapi::dpl::reduce(oneapi::dpl::execution::par_unseq, v.begin(), v.end(), 0L);

    const long n = v.size();
    if (v.front() != 1 || v.back() != n || sum != n * (n + 1) / 2) {
        std::cout << "oneDPL sort/reduce gave a wrong result" << std::endl;
        return 1;
    }
    std::cout << "OK sum = " << sum << std::endl;
    return 0;
}
