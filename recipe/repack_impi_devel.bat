@echo on
set "src=%SRC_DIR%\%PKG_NAME%"

pushd %SRC_DIR%
  FOR /F "usebackq tokens=1" %%i IN (`DIR /S/B *.conda` ) DO (
    echo "Converting .conda to .tar.bz2"
    cph transmute %%i .tar.bz2
    del %%i
  )

  FOR /F "usebackq tokens=1" %%i IN (`DIR /S/B *.tar.bz2` ) DO (
    echo "Extracting .tar.bz2"
    cph extract %%i --dest %%i\..
    del %%i
  )
popd

robocopy /E "%src%" "%PREFIX%"
if %ERRORLEVEL% GEQ 8 exit 1

:: replace old info folder with our new regenerated one
rd /s /q %PREFIX%\info

:: Inject Fortran files from patch directory
echo "Injecting Fortran files for Windows MPI support..."

set "PATCH_DIR=%~dp0patch\mpi"

if exist "%PATCH_DIR%" (
    echo "Copying Fortran files from patch directory..."

    :: Create include directory if it doesn't exist
    if not exist "%LIBRARY_INC%" mkdir "%LIBRARY_INC%"

    :: Copy header files
    if exist "%PATCH_DIR%\mpif.h" copy "%PATCH_DIR%\mpif.h" "%LIBRARY_INC%\" /Y
    if exist "%PATCH_DIR%\mpiof.h" copy "%PATCH_DIR%\mpiof.h" "%LIBRARY_INC%\" /Y

    :: Copy module files
    if exist "%PATCH_DIR%\mpi" (
        robocopy "%PATCH_DIR%\mpi" "%LIBRARY_INC%\mpi" /E /NFL /NDL
        if %ERRORLEVEL% GEQ 8 (
            echo "Error copying Fortran modules"
            exit 1
        )
    )

    echo "Successfully injected Fortran files into Windows MPI package"
) else (
    echo "Warning: Fortran patch directory not found at %PATCH_DIR%"
    echo "Windows MPI package will be missing Fortran support"
)