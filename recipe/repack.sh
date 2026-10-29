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

# The Intel upstream packages install license files to a shared path
# (share/doc/mkl/licensing/) which causes conda ClobberWarnings when multiple
# packages (e.g. mkl and mkl-include) are installed together into the same env.
# Move them to a per-package unique path to avoid the conflict.
if [ -d "$PREFIX/share/doc/mkl/licensing" ] && [ "$PKG_NAME" != "mkl" ]; then
    mkdir -p "$PREFIX/share/doc/$PKG_NAME/licensing"
    mv "$PREFIX/share/doc/mkl/licensing"/* "$PREFIX/share/doc/$PKG_NAME/licensing/"
    rm -rf "$PREFIX/share/doc/mkl/licensing"
fi

# impi_rt 2021.19 no longer ships fi_info, and conda sources this hook into a shell that
# may run under `set -e` (other packages' post-link scripts), so a failing `which fi_info`
# aborts the whole install.
deact="$PREFIX/etc/conda/deactivate.d/mpivars.deactivate.sh"
if [ "$PKG_NAME" = "impi_rt" ] && [ -f "$deact" ]; then
    sed -i 's/FIP=`which fi_info`/FIP=$(command -v fi_info 2>\/dev\/null || true)/' "$deact"
    if grep -q 'which fi_info' "$deact"; then
        echo "mpivars.deactivate.sh patch did not apply" >&2
        exit 1
    fi
fi
