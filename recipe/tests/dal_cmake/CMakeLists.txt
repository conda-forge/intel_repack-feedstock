cmake_minimum_required(VERSION 3.12)
project(dal_smoke LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)

# ONEDAL_LINK=dynamic|static is passed on the command line
set(ONEDAL_USE_DPCPP no)
set(ONEDAL_INTERFACE yes)
find_package(oneDAL REQUIRED)

add_executable(dal_mean ${CMAKE_CURRENT_SOURCE_DIR}/../src/dal_mean.cpp)
if(ONEDAL_LINK STREQUAL "static")
  # the static archives (and the MKL ones they pull in) reference each other
  target_link_libraries(dal_mean PRIVATE -Wl,--start-group ${oneDAL_IMPORTED_TARGETS} -Wl,--end-group)
else()
  target_link_libraries(dal_mean PRIVATE ${oneDAL_IMPORTED_TARGETS})
endif()
