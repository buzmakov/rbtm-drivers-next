@echo Using jenkins at %JENKINS_HOME%, node %NODE_NAME%
@echo Using parameters %NODE_LABELS%
@echo Use hg revision %XIMC_REVISION%
@echo Use JDK %JDK_HOME%

@if 'x%MERCURIAL%'=='x' set MERCURIAL=hg
@if "x%JDK_HOME%"=='x' goto FAIL

set BASEDIR=%CD%
:: reset errorrevel
@cmd /C exit 0

:: Build hash could be specified by jenkins
@if 'x%XIMC_REVISION%' NEQ 'x' @set MERCURIAL_SUFFIX=-r %XIMC_REVISION%
@echo Using checkout command: hg update -c %MERCURIAL_SUFFIX%
@if 'x%SKIP_CLEAN_CHECKOUT%' NEQ 'x' goto SKIP_CLEAN_CHECKOUT
:: pull again because working copy often contain only one branch
%MERCURIAL% pull
@if not %errorlevel% == 0 goto FAIL
:: update -c fails on uncommited changes
%MERCURIAL% update -c %MERCURIAL_SUFFIX%
@if not %errorlevel% == 0 goto FAIL

:SKIP_CLEAN_CHECKOUT
:: purge drop all non-added files
%MERCURIAL% purge -a
@if not %errorlevel% == 0 goto FAIL
::  %MERCURIAL% update -c
::  @if not %errorlevel% == 0 goto FAIL
@if exist %DISTDIR% rmdir /S /Q %DISTDIR%
@if not %errorlevel% == 0 goto FAIL

@echo Launching build itself
call build.bat
@if not %errorlevel% == 0 goto FAIL

@echo Packaging
@if "%NODE_NAME%" == "" goto SUCCESS
c:\cygwin\bin\bash.exe --login -c "cd `cygpath '%BASEDIR%'` && tar cf results-dist-%NODE_NAME%.tar ximc"
@if not %errorlevel% == 0 goto FAIL

:: it is an exit
:SUCCESS
@echo CI build succeeded
@goto :eof

:FAIL
@echo CI build failed
exit /B 1

