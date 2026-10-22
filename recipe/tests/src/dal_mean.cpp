// Link against oneDAL (shared or static) and check a computed result.
#include <iostream>

#include "oneapi/dal/algo/basic_statistics.hpp"
#include "oneapi/dal/table/homogen.hpp"
#include "oneapi/dal/table/row_accessor.hpp"

namespace dal = oneapi::dal;
namespace bs = oneapi::dal::basic_statistics;

int main() {
    // 3 rows x 2 columns; column means are 3 and 4
    const float data[] = {1, 2, 3, 4, 5, 6};
    const auto table = dal::homogen_table::wrap(data, 3, 2);

    const auto desc = bs::descriptor<float>{}.set_result_options(bs::result_options::mean);
    const auto result = dal::compute(desc, table);
    const auto mean = dal::row_accessor<const float>(result.get_mean()).pull();

    if (mean.get_count() != 2 || mean[0] != 3.0f || mean[1] != 4.0f) {
        std::cout << "basic_statistics mean is wrong" << std::endl;
        return 1;
    }
    std::cout << "OK mean = " << mean[0] << ", " << mean[1] << std::endl;
    return 0;
}
