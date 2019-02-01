@if 'x%MERCURIAL%'=='x' set MERCURIAL=hg
:: reset errorrevel
@cmd /C exit 0

@set BASEDIR=%CD%
@set DISTDIR=ximc
@set DEPSDIR=deps

@set GIT="%ProgramFiles%\Git\bin\git.exe" 
@set CMAKE="%ProgramFiles(x86)%\CMake\bin\cmake.exe" 

@if "%1" == "cleandist" call :CLEAN ; exit /B 0

:: JDK_HOME must be set
@echo JDK home is %JDK_HOME%
@if "x%JDK_HOME%"=="x" goto FAIL

:: read vers
set BINDYVER=
set XIWRAPPERVER=
for /F %%i in (' c:\cygwin\bin\bash.exe --login -c "sed '3q;d' `cygpath '%BASEDIR%\version'`" ') do set BINDYVER=%%i
for /F %%i in (' c:\cygwin\bin\bash.exe --login -c "sed '4q;d' `cygpath '%BASEDIR%\version'`" ') do set XIWRAPPERVER=%%i
if "%BINDYVER%" == "" set BINDYVER=master
if "%XIWRAPPERVER%" == "" set XIWRAPPERVER=default
echo Found bindy ver %BINDYVER%
echo Found xiwrapper ver %XIWRAPPERVER%

:: debug flag
@set CONFIGURATION=Debug
@if "x%DEBUG%"=="xtrue" goto :CONF_DEBUG
@set CONFIGURATION=Release
:CONF_DEBUG
echo Configuration %CONFIGURATION%

:: -------------------------------------
:: ---------- entry point --------------

@if "%VSINSTALLDIR%" == "" call "%VS120COMNTOOLS%/vsvars32.bat"
@if not %errorlevel% == 0 goto FAIL
@if "%VSINSTALLDIR%" == "" call "%VCINSTALLDIR%/vcvarsall.bat" x86_amd64
@if not %errorlevel% == 0 goto FAIL

call :CLEAN
@if not %errorlevel% == 0 goto FAIL
call :LIB
@if not %errorlevel% == 0 goto FAIL
call :EXAMPLES
@if not %errorlevel% == 0 goto FAIL

:: it is an exit
:SUCCESS
@echo SUCCESS
@goto :eof

:FAIL
@echo FAIL
exit /B 1

:: ----------------------------
:: ---------- clean -----------
:CLEAN
%MERCURIAL% purge -a -X %DEPSDIR%
@if not %errorlevel% == 0 goto FAIL
::  %MERCURIAL% update -c
::  @if not %errorlevel% == 0 goto FAIL
@if exist %DISTDIR% rmdir /S /Q %DISTDIR%
@if not %errorlevel% == 0 goto FAIL
goto :eof

:: ----------------------------------------
:: ---------- build entry point -----------
:LIB
::goto SKIP_DEPS
call :DEPS_BINDY win64 x64
@if not %errorlevel% == 0 goto FAIL
call :DEPS_XIWRAPPER win64 x64
@if not %errorlevel% == 0 goto FAIL
call :DEPS_BINDY win32 Win32
@if not %errorlevel% == 0 goto FAIL
call :DEPS_XIWRAPPER win32 Win32
@if not %errorlevel% == 0 goto FAIL

:SKIP_DEPS
call :LIBXIMC win32 Win32
@if not %errorlevel% == 0 goto FAIL
call :LIBXIMC win64 x64
@if not %errorlevel% == 0 goto FAIL
call :WRAPPER_JAVA win32 Win32 "%JDK32_HOME%"
@if not %errorlevel% == 0 goto FAIL
call :WRAPPER_JAVA win64 x64 "%JDK_HOME%"
@if not %errorlevel% == 0 goto FAIL
call :WRAPPER_CSHARP win32 Win32
@if not %errorlevel% == 0 goto FAIL
call :WRAPPER_CSHARP win64 x64
@if not %errorlevel% == 0 goto FAIL
call :WRAPPER_DELPHI
@if not %errorlevel% == 0 goto FAIL
call :WRAPPER_MATLAB
@if not %errorlevel% == 0 goto FAIL
goto :eof

:: --------------------------------------
:: ------------ deps bindy --------------
:DEPS_BINDY
@set DISTARCH=%DEPSDIR%\%1
@set ARCH=%2
@echo Building bindy for %ARCH%...

rmdir /S /Q %DISTARCH%\bindy
mkdir %DISTARCH%\bindy

@set URL="https://github.com/EPC-MSU/Bindy.git"
::@set URL=%USERPROFILE%\Documents\bindy

%GIT% clone --recursive %URL% %DISTARCH%\bindy
@if not %errorlevel% == 0 goto FAIL
cd %DISTARCH%\bindy
%GIT% checkout %BINDYVER%
@if not %errorlevel% == 0 goto FAIL
%GIT% submodule update --init --recursive
@if not %errorlevel% == 0 goto FAIL
%GIT% submodule update --recursive
@if not %errorlevel% == 0 goto FAIL

%GIT% --no-pager show --stat %BINDYVER%
@set GENERATOR=Visual Studio 12 2013
if %ARCH% == x64 @set GENERATOR=%GENERATOR% Win64
%CMAKE% -G "%GENERATOR%" .
@set LASTERR=%errorlevel%
cd %BASEDIR%
@if not %LASTERR% == 0 goto FAIL
msbuild %DISTARCH%\bindy\bindy.sln /p:Configuration=%CONFIGURATION% /p:Platform=%ARCH%
@if not %errorlevel% == 0 goto FAIL
if not exist %DISTARCH%\bindy\%CONFIGURATION%\bindy.dll goto FAIL
@if not exist %DISTDIR%\%1 mkdir %DISTDIR%\%1
@if not %errorlevel% == 0 goto FAIL
copy %DISTARCH%\bindy\%CONFIGURATION%\bindy.dll %DISTDIR%\%1
@if not %errorlevel% == 0 goto FAIL
copy %DISTARCH%\bindy\sample_keyfile.sqlite %DISTDIR%\%1\keyfile.sqlite
@if not %errorlevel% == 0 goto FAIL

@if not "x%DEBUG%" == "xtrue" goto SKIP_PDB_COPY_BINDY
copy %DISTARCH%\bindy\%CONFIGURATION%\bindy.pdb %DISTDIR%\%1
@if not %errorlevel% == 0 goto FAIL
:SKIP_PDB_COPY_BINDY

@echo Building bindy for %ARCH% completed
@goto :eof

:: --------------------------------------
:: ------------ deps xiwrapper -------------
:DEPS_XIWRAPPER
@set DISTARCH=%DEPSDIR%\%1
@set ARCH=%2
@echo Building xiwrapper for %ARCH%...

rmdir /S /Q %DISTARCH%\xiwrapper
mkdir %DISTARCH%\xiwrapper

@set URL="https://anonymous:anonymous@hg.ximc.ru/libxiwrapper"
::@set URL=%USERPROFILE%\Documents\xiwrapper
%MERCURIAL% clone %URL% %DISTARCH%\xiwrapper
@if not %errorlevel% == 0 goto FAIL
cd %DISTARCH%\xiwrapper
%MERCURIAL% checkout %XIWRAPPERVER%
@if not %errorlevel% == 0 goto FAIL
%MERCURIAL% log -r %XIWRAPPERVER%
@if not %errorlevel% == 0 goto FAIL
@set GENERATOR=Visual Studio 12 2013
if %ARCH% == x64 @set GENERATOR=%GENERATOR% Win64
%CMAKE% -G "%GENERATOR%" -DBINDY_PATH=%BASEDIR%\%DISTARCH%\bindy .
@set LASTERR=%errorlevel%
cd %BASEDIR%
@if not %LASTERR% == 0 goto FAIL
msbuild %DISTARCH%\xiwrapper\xiwrapper.sln /p:Configuration=%CONFIGURATION% /p:Platform=%ARCH%
@if not %errorlevel% == 0 goto FAIL
if not exist %DISTARCH%\xiwrapper\%CONFIGURATION%\xiwrapper.dll goto FAIL
@if not exist %DISTDIR%\%1 mkdir %DISTDIR%\%1
@if not %errorlevel% == 0 goto FAIL
copy %DISTARCH%\xiwrapper\%CONFIGURATION%\xiwrapper.dll %DISTDIR%\%1
@if not %errorlevel% == 0 goto FAIL

@if not "x%DEBUG%" == "xtrue" goto SKIP_PDB_COPY_XIWRAPPER
copy %DISTARCH%\xiwrapper\%CONFIGURATION%\xiwrapper.pdb %DISTDIR%\%1
@if not %errorlevel% == 0 goto FAIL
:SKIP_PDB_COPY_XIWRAPPER

@echo Building xiwrapper for %ARCH% completed
@goto :eof


:: --------------------------------------
:: -------------- libximc ---------------
:LIBXIMC
@set DISTARCH=%DISTDIR%\%1
@set ARCH=%2
@echo Building libximc for %ARCH%...
@set BINDIR=%CONFIGURATION%-%ARCH%

%MERCURIAL% purge -a -X %DEPSDIR%
@if not %errorlevel% == 0 goto FAIL
@if not exist %DISTARCH% mkdir %DISTARCH%
@if not %errorlevel% == 0 goto FAIL

msbuild libximc.sln /p:Configuration=%CONFIGURATION% /p:Platform=%ARCH% /t:xigen;libximc
@if not %errorlevel% == 0 goto FAIL
copy %BINDIR%\libximc.dll %DISTARCH%
@if not %errorlevel% == 0 goto FAIL
@if not "x%DEBUG%" == "xtrue" goto SKIP_PDB_COPY_LIBXIMC
copy %BINDIR%\*.pdb %DISTARCH%
@if not %errorlevel% == 0 goto FAIL
:SKIP_PDB_COPY_LIBXIMC
copy %BINDIR%\libximc.lib %DISTARCH%
@if not %errorlevel% == 0 goto FAIL
copy libximc\src\libximc.def %DISTARCH%
@if not %errorlevel% == 0 goto FAIL
copy libximc\include\ximc.h %DISTARCH%
@if not %errorlevel% == 0 goto FAIL

@echo Building for %ARCH% completed
@goto :eof

:: ------------------------------------
:: ---------- csharp wrapper ---------- 
:WRAPPER_CSHARP
@echo Building csharp wrapper
@set DISTARCH=%DISTDIR%\%1
@set BINDIR=wrappers\csharp\bin\%CONFIGURATION%-%2

%MERCURIAL% purge -a -X %DEPSDIR%
@if not %errorlevel% == 0 goto FAIL
@if not exist %DISTARCH% mkdir %DISTARCH%
@if not %errorlevel% == 0 goto FAIL

msbuild libximc.sln /p:Configuration=%CONFIGURATION% /p:Platform=Win32 /t:xigen
@if not %errorlevel% == 0 goto FAIL
msbuild wrappers\csharp\ximcnet.sln /p:Configuration=%CONFIGURATION% /p:Platform=%2
@if not %errorlevel% == 0 goto FAIL
copy %BINDIR%\ximcnet.dll %DISTARCH%
@if not %errorlevel% == 0 goto FAIL
copy wrappers\csharp\src\ximcnet.cs %DISTARCH%
@if not %errorlevel% == 0 goto FAIL

@echo Building sharp wrapper completed
@goto :eof

:: ------------------------------------
:: ---------- delphi wrapper ---------- 
:WRAPPER_DELPHI
@echo Generating pascal wrapper
@set DISTARCH=%DISTDIR%\win32

%MERCURIAL% purge -a -X %DEPSDIR%
@if not %errorlevel% == 0 goto FAIL

msbuild libximc.sln /p:Configuration=%CONFIGURATION% /p:Platform=Win32 /t:xigen
@if not %errorlevel% == 0 goto FAIL
%CONFIGURATION%-Win32\xigen.exe --gen-pascal -x version -i libximc\src\protocol.xi -o wrappers\delphi\ximc.pas -t wrappers\delphi\ximc-template.pas
@if not %errorlevel% == 0 goto FAIL

copy wrappers\delphi\ximc.pas %DISTARCH%
@if not %errorlevel% == 0 goto FAIL

@echo Generating pascal wrapper completed
@goto :eof

:: ------------------------------------
:: ---------- java wrapper ---------- 
:WRAPPER_JAVA
@set DISTARCH=%DISTDIR%\%1
@set ARCH=%2
@set JPATH=%3
@echo Generating java wrapper for %ARCH% and %JPATH%
@set GENDIR=wrappers\java\gen
@set BINDIR=%CONFIGURATION%-%ARCH%\

%MERCURIAL% purge -a -X %DEPSDIR%
@if not %errorlevel% == 0 goto FAIL

@if not exist %GENDIR% mkdir %GENDIR%

msbuild libximc.sln /p:Configuration=%CONFIGURATION% /p:Platform=%ARCH% /t:xigen
@if not %errorlevel% == 0 goto FAIL

%CONFIGURATION%-%ARCH%\xigen.exe --gen-java -x version -i libximc\src\protocol.xi -o wrappers\java\src\java\ru\ximc\libximc\JXimc.java -t wrappers\java\src\java\\ru\ximc\libximc\JXimc-template.java
@if not %errorlevel% == 0 goto FAIL

%JPATH%\bin\javac -Xlint -d wrappers\java wrappers\java\src\java\ru\ximc\libximc\JXimc.java wrappers\java\src\java\ru\ximc\libximc\XimcError.java wrappers\java\src\java\ru\ximc\libximc\XimcNoDevice.java wrappers\java\src\java\ru\ximc\libximc\XimcNotImplemented.java wrappers\java\src\java\ru\ximc\libximc\XimcValueError.java
@if not %errorlevel% == 0 goto FAIL

%JPATH%\bin\jar cf wrappers\java\libjximc.jar -C wrappers\java ru 
@if not %errorlevel% == 0 goto FAIL

%JPATH%\bin\javah -classpath wrappers\java\libjximc.jar -jni -d %GENDIR% ru.ximc.libximc.JXimc
@if not %errorlevel% == 0 goto FAIL

%CONFIGURATION%-%ARCH%\xigen.exe --gen-jni -x version -i libximc\src\protocol.xi -o wrappers\java\src\c\ru_ximc_libximc_JXimc-gen.c -t wrappers\java\src\c\ru_ximc_libximc_JXimc-template.c
@if not %errorlevel% == 0 goto FAIL

msbuild libximc.sln /p:Configuration=%CONFIGURATION% /p:Platform=%ARCH% /t:libjximc
@if not %errorlevel% == 0 goto FAIL

copy wrappers\java\libjximc.jar %DISTARCH%
@if not %errorlevel% == 0 goto FAIL

copy %BINDIR%\libjximc.dll %DISTARCH%
@if not %errorlevel% == 0 goto FAIL

@echo Generating java wrapper completed
@goto :eof


:: ------------------------------------
:: ---------- matlab wrapper ---------- 
:WRAPPER_MATLAB
@echo Building matlab wrapper
@set DISTARCH=%DISTDIR%\win64
@set BINDIR=%DISTARCH%\wrappers\matlab

@if not exist %BINDIR% mkdir %BINDIR%
@if not %errorlevel% == 0 goto FAIL

copy %DISTARCH%\bindy.dll wrappers\matlab\
copy %DISTARCH%\xiwrapper.dll wrappers\matlab\
copy %DISTARCH%\libximc.dll wrappers\matlab\

@if not %errorlevel% == 0 goto FAIL
cd wrappers\matlab
matlab.exe -nodesktop -wait -r buildm -logfile buildm.log
@set LASTERR=%errorlevel%
cd %BASEDIR%
@if not %LASTERR% == 0 goto FAIL

move wrappers\matlab\ximcm.m %BINDIR%
@if not %errorlevel% == 0 goto FAIL

move wrappers\matlab\libximc_thunk_pcwin64.dll %BINDIR%
@if not %errorlevel% == 0 goto FAIL

copy wrappers\matlab\ximcm.h %BINDIR%
@if not %errorlevel% == 0 goto FAIL

@echo Building matlab wrapper completed
@goto :eof

:: ------------------------------
:: ---------- examples ---------- 
:EXAMPLES
%MERCURIAL% purge -a -X %DEPSDIR%
@if not %errorlevel% == 0 goto FAIL
:: -----
@set NAME=testapp
@echo Building example %NAME%...
msbuild examples\%NAME%\%NAME%.sln /p:Configuration=%CONFIGURATION% /p:Platform=Win32
@if not %errorlevel% == 0 goto FAIL
mkdir %DISTDIR%\win32\%NAME%-compiled-win32
copy examples\%NAME%\compiled-win32\* %DISTDIR%\win32\%NAME%-compiled-win32\*
@if not %errorlevel% == 0 goto FAIL
msbuild examples\%NAME%\%NAME%.sln /p:Configuration=%CONFIGURATION% /p:Platform=x64
@if not %errorlevel% == 0 goto FAIL
mkdir %DISTDIR%\win64\%NAME%-compiled-win64
copy examples\%NAME%\compiled-win64\* %DISTDIR%\win64\%NAME%-compiled-win64\*
@if not %errorlevel% == 0 goto FAIL

@if not "x%DEBUG%" == "xtrue" goto SKIP_PDB_COPY_TESTAPP
:: TODO: Bug will be here
copy examples\%NAME%\%CONFIGURATION%-Win32\%NAME%.pdb %DISTDIR%\win32
@if not %errorlevel% == 0 goto FAIL
copy examples\%NAME%\%CONFIGURATION%-x64\%NAME%.pdb %DISTDIR%\win64
@if not %errorlevel% == 0 goto FAIL
:SKIP_PDB_COPY_TESTAPP

:: -----
@set NAME=testappeasy
@echo Building example %NAME%...
msbuild examples\%NAME%\%NAME%.sln /p:Configuration=%CONFIGURATION% /p:Platform=Win32
@if not %errorlevel% == 0 goto FAIL
mkdir %DISTDIR%\win32\%NAME%-compiled-win32
copy examples\%NAME%\compiled-win32\* %DISTDIR%\win32\%NAME%-compiled-win32\*
@if not %errorlevel% == 0 goto FAIL
msbuild examples\%NAME%\%NAME%.sln /p:Configuration=%CONFIGURATION% /p:Platform=x64
@if not %errorlevel% == 0 goto FAIL
mkdir %DISTDIR%\win64\%NAME%-compiled-win64
copy examples\%NAME%\compiled-win64\* %DISTDIR%\win64\%NAME%-compiled-win64\*
@if not %errorlevel% == 0 goto FAIL
:: -----
@set NAME=testcprofile
@echo Building example %NAME%...
msbuild examples\%NAME%\%NAME%.sln /p:Configuration=%CONFIGURATION% /p:Platform=Win32
@if not %errorlevel% == 0 goto FAIL
mkdir %DISTDIR%\win32\%NAME%-compiled-win32
copy examples\%NAME%\compiled-win32\* %DISTDIR%\win32\%NAME%-compiled-win32\*
@if not %errorlevel% == 0 goto FAIL
msbuild examples\%NAME%\%NAME%.sln /p:Configuration=%CONFIGURATION% /p:Platform=x64
@if not %errorlevel% == 0 goto FAIL
mkdir %DISTDIR%\win64\%NAME%-compiled-win64
copy examples\%NAME%\compiled-win64\* %DISTDIR%\win64\%NAME%-compiled-win64\*
@if not %errorlevel% == 0 goto FAIL
:: -----
@set NAME=testcodeblocks
@echo Building example %NAME%...
@SET MINGW32=C:\Program Files (x86)\mingw-w64\i686-7.3.0-posix-dwarf-rt_v5-rev0\mingw32\bin
@SET MINGW64=C:\Program Files\mingw-w64\x86_64-7.3.0-posix-seh-rt_v5-rev0\mingw64\bin
@SET CBP=C:\Program Files (x86)\CodeBlocks\cbp2make.exe
@SET PATH_BASE=%PATH%;
:: Win32
@SET PATH=%PATH_BASE%;%MINGW32%
"%CBP%" -in examples\%NAME%\%NAME%.cbp -out examples\%NAME%\makefile -windows -targets "win32" 
@if not %errorlevel% == 0 goto FAIL
mingw32-make --directory examples\%NAME%
@if not %errorlevel% == 0 goto FAIL
del examples\%NAME%\obj /Q
mkdir %DISTDIR%\win32\%NAME%-compiled-win32
copy examples\%NAME%\compiled-win32\* %DISTDIR%\win32\%NAME%-compiled-win32\*
@if not %errorlevel% == 0 goto FAIL
:: Win64
@SET PATH=%PATH_BASE%;%MINGW64%
"%CBP%" -in examples\%NAME%\%NAME%.cbp -out examples\%NAME%\makefile -windows -targets "win64"
@if not %errorlevel% == 0 goto FAIL
mingw32-make --directory examples\%NAME%
@if not %errorlevel% == 0 goto FAIL
del examples\%NAME%\obj /Q
mkdir %DISTDIR%\win64\%NAME%-compiled-win64
copy examples\%NAME%\compiled-win64\* %DISTDIR%\win64\%NAME%-compiled-win64\*
@if not %errorlevel% == 0 goto FAIL
::   clear env
@SET PATH=%PATH_BASE%
:: -----
@set NAME=testcs
@echo Building example %NAME%...
:: Win32
copy %DISTDIR%\win32\ximcnet.dll examples\%NAME%\
msbuild examples\%NAME%\%NAME%.sln /p:Configuration=%CONFIGURATION% /p:Platform=Win32
@if not %errorlevel% == 0 goto FAIL
mkdir %DISTDIR%\win32\%NAME%-compiled-win32
copy examples\%NAME%\compiled-win32\* %DISTDIR%\win32\%NAME%-compiled-win32\*
@if not %errorlevel% == 0 goto FAIL
:: x64
copy %DISTDIR%\win64\ximcnet.dll examples\%NAME%
msbuild examples\%NAME%\%NAME%.sln /p:Configuration=%CONFIGURATION% /p:Platform=x64
@if not %errorlevel% == 0 goto FAIL
mkdir %DISTDIR%\win64\%NAME%-compiled-win64
copy examples\%NAME%\compiled-win64\* %DISTDIR%\win64\%NAME%-compiled-win64\*
@if not %errorlevel% == 0 goto FAIL
:: -----
@set NAME=testvbnet
@echo Building example %NAME%...
:: Win32
copy %DISTDIR%\win32\ximcnet.dll examples\%NAME%
msbuild examples\%NAME%\%NAME%.sln /p:Configuration=%CONFIGURATION% /p:Platform=Win32
@if not %errorlevel% == 0 goto FAIL
mkdir %DISTDIR%\win32\%NAME%-compiled-win32
copy examples\%NAME%\compiled-win32\* %DISTDIR%\win32\%NAME%-compiled-win32\*
@if not %errorlevel% == 0 goto FAIL
:: x64
copy %DISTDIR%\win64\ximcnet.dll examples\%NAME%
msbuild examples\%NAME%\%NAME%.sln /p:Configuration=%CONFIGURATION% /p:Platform=x64
@if not %errorlevel% == 0 goto FAIL
mkdir %DISTDIR%\win64\%NAME%-compiled-win64
copy examples\%NAME%\compiled-win64\* %DISTDIR%\win64\%NAME%-compiled-win64\*
@if not %errorlevel% == 0 goto FAIL
:: -----
@set NAME=testdelphi
@echo Building example %NAME%...
"%PROGRAMFILES(x86)%\Borland\Delphi6\Bin\DCC32.EXE" -U%DISTDIR%\win32 examples\%NAME%\%NAME%.dpr
@if not %errorlevel% == 0 goto FAIL
copy examples\%NAME%\%NAME%.exe %DISTDIR%\win32
@if not %errorlevel% == 0 goto FAIL
:: -----
@set NAME=testjava
@echo Building example %NAME% 64-bit...
"%JDK_HOME%\bin\javac" -Xlint -classpath %DISTDIR%\win64\libjximc.jar -d examples\%NAME% examples\%NAME%\ru\ximc\TestJava.java
@if not %errorlevel% == 0 goto FAIL
"%JDK_HOME%\bin\jar" cmf examples\%NAME%\MANIFEST.MF examples\%NAME%\%NAME%.jar -C examples\%NAME% ru 
@if not %errorlevel% == 0 goto FAIL
copy examples\%NAME%\%NAME%.jar %DISTDIR%\win64
@if not %errorlevel% == 0 goto FAIL
:: -----
@set NAME=testjava
@echo Building example %NAME% 32-bit...
"%JDK32_HOME%\bin\javac" -Xlint -classpath %DISTDIR%\win32\libjximc.jar -d examples\%NAME% examples\%NAME%\ru\ximc\TestJava.java
@if not %errorlevel% == 0 goto FAIL
"%JDK32_HOME%\bin\jar" cmf examples\%NAME%\MANIFEST.MF examples\%NAME%\%NAME%.jar -C examples\%NAME% ru 
@if not %errorlevel% == 0 goto FAIL
copy examples\%NAME%\%NAME%.jar %DISTDIR%\win32
@if not %errorlevel% == 0 goto FAIL
:: -----
@goto :eof

