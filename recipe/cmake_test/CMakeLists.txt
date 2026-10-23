cmake_minimum_required(VERSION 3.12)
project(cf_dummy LANGUAGES C CXX)
find_package(MKL REQUIRED)

add_executable(mkl_dgemm ${CMAKE_CURRENT_SOURCE_DIR}/../tests/src/mkl_dgemm.c)
target_link_libraries(mkl_dgemm PRIVATE MKL::MKL)
