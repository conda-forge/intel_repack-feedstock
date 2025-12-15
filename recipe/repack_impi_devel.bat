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
echo.
echo ========================================
echo Injecting Fortran files for Windows MPI
echo ========================================

set "PATCH_DIR=%RECIPE_DIR%\patch\mpi"
echo PATCH_DIR=%PATCH_DIR%
echo LIBRARY_INC=%LIBRARY_INC%
echo RECIPE_DIR=%RECIPE_DIR%

if not exist "%PATCH_DIR%" (
    echo ERROR: Fortran patch directory not found at %PATCH_DIR%
    echo Windows MPI package will be missing Fortran support
    echo ========================================
    goto :EOF
)

echo Patch directory found!
echo.
echo Listing patch directory contents:
dir "%PATCH_DIR%"
echo.

:: Create include directory if it doesn't exist
if not exist "%LIBRARY_INC%" mkdir "%LIBRARY_INC%"

:: Copy header files
echo Copying Fortran header files...
copy "%PATCH_DIR%\mpif.h" "%LIBRARY_INC%\" /Y
if errorlevel 1 (
    echo ERROR: Failed to copy mpif.h
    exit /b 1
)
echo   - mpif.h copied successfully

copy "%PATCH_DIR%\mpiof.h" "%LIBRARY_INC%\" /Y
if errorlevel 1 (
    echo ERROR: Failed to copy mpiof.h
    exit /b 1
)
echo   - mpiof.h copied successfully

:: Copy module files
echo.
echo Copying Fortran module files...
if not exist "%LIBRARY_INC%\mpi" mkdir "%LIBRARY_INC%\mpi"
robocopy "%PATCH_DIR%\mpi" "%LIBRARY_INC%\mpi" /E
if %ERRORLEVEL% GEQ 8 (
    echo ERROR: robocopy failed with error level %ERRORLEVEL%
    exit /b 1
)
echo   - Fortran modules copied successfully (robocopy exit code: %ERRORLEVEL%)

echo.
echo Verifying copied files...
if not exist "%LIBRARY_INC%\mpif.h" (
    echo ERROR: mpif.h not found after copy!
    exit /b 1
)
echo   - mpif.h verified

if not exist "%LIBRARY_INC%\mpiof.h" (
    echo ERROR: mpiof.h not found after copy!
    exit /b 1
)
echo   - mpiof.h verified

if not exist "%LIBRARY_INC%\mpi\mpi.mod" (
    echo ERROR: mpi.mod not found after copy!
    exit /b 1
)
echo   - mpi.mod verified

if not exist "%LIBRARY_INC%\mpi\mpi_f08.mod" (
    echo ERROR: mpi_f08.mod not found after copy!
    exit /b 1
)
echo   - mpi_f08.mod verified

echo.
echo Successfully injected Fortran files into Windows MPI package
echo ========================================
