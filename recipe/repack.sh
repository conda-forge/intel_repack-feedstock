#!/bin/bash
set -ex

# for subpackages, we have named our extracted locations according to the subpackage name
#    That's what this $PKG_NAME is doing - picking the right subfolder to rsync

# Extracting .conda files since conda-build
for conda_file in `find . -name '*.conda'`; do \
  DIR_NAME=$(dirname $conda_file)
  cph transmute "${conda_file}" .tar.bz2 ;
  rm ${conda_file} ;
  for tar_file in `find . -name '*.tar.bz2'`; do \
    tar xjvf "${tar_file}" -C ${DIR_NAME} ;
    rm ${tar_file}
  done
done

src="$SRC_DIR/$PKG_NAME"
cp -av "$src"/* "$PREFIX/"

# replace old info folder with our new regenerated one
rm -rf "$PREFIX/info"

# tcm bundles hwloc; use conda-forge's libhwloc (same soname) instead so the
# two packages don't clobber each other's libhwloc.so* files.
if [ "$PKG_NAME" == "tcm" ]; then
    rm -f "$PREFIX"/lib/libhwloc.so*
fi

# The Intel upstream packages install license files to a shared path
# (share/doc/mkl/licensing/) which causes conda ClobberWarnings when multiple
# packages (e.g. mkl and mkl-include) are installed together into the same env.
# Move them to a per-package unique path to avoid the conflict.
if [ -d "$PREFIX/share/doc/mkl/licensing" ] && [ "$PKG_NAME" != "mkl" ]; then
    mkdir -p "$PREFIX/share/doc/$PKG_NAME/licensing"
    mv "$PREFIX/share/doc/mkl/licensing"/* "$PREFIX/share/doc/$PKG_NAME/licensing/"
    rm -rf "$PREFIX/share/doc/mkl/licensing"
fi
