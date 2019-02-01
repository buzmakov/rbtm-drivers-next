/*!
 * \mainpage libximc library
 *
 * Documentation for libximc library.
 *
 * \image html logo.png
 *
 * Libximc is cross-platform library for working with ximc 8SMC4 and 8SMC5 controllers.
 *
 * Full documentation about ximc controllers is <a href="https://doc.xisupport.com">there</a>
 *
 * Full documentation about libximc API is available on the page \ref ximc.h.
 *
 * \section about_ximc About ximc
 *
 * We offer an inexpensive and ultra-compact servo-drive with USB interface for stepper motors with external power supply.
 * Forget about cumbersome and expensive servo-drives! All you need is a stepper motor, a controller, a USB cable and any stabilized external power supply. That is all! Forget about active coolers as well. Controller's board is about the same size as a notepad or a cellphone, therefore, you may just put it down on the worktable without any assembly procedures. The controller works with any type of compact stepper motors with the rated winding current of up to 3A. Controller works with stepper motors with no feedback as well as with ones equipped with encoders in feedback loop, including linear encoders on the stages. The motor connector on the controller board is the same as one used by Standa company and it fits to all the Standa stages. USB connector provides easy communication and work with computer. Several controllers can be connected to one computer either via USB ports or through a special backplane supplied with multiaxis systems. The controller is fully compatible with the majority of operating systems, e.g., Windows, Mac OS X, Linux, etc.
 *
 * \section about_libximc About libximc
 * Congratulations on choosing XIMC multi-platform programming library! This document contains all information about XIMC library. It utilizes well known virtual COM-port interface, so you can use it on Windows 7, Windows Vista, Windows XP, Windows Server 2003, Windows 2000, Linux, Mac OS X. 
 * XIMC multi-platform programing library supports plug/unplug on the fly. 
 * Each device can be controlled only by one program at once. 
 * Multiple processes (programs) that control one device simultaneously are not allowed.
 *
 * Please read the \ref intro_sec to start work with library.
 *
 * To use libximc in your project please consult with \ref howtouse_sec
 *
 * \page intro_sec Introduction
 *
 * \section about_sec About
 *
 * Congratulations on choosing XIMC multi-platform programming library!
 * This document contains all information about XIMC library.
 * It utilizes well known virtual COM-port interface, so you can use it on Windows 7, Windows
 * Vista, Windows XP, Windows Server 2003, Windows 2000, Linux, Mac OS X.
 * XIMC multi-platform programing library supports plug/unplug on the fly.
 * Each device can be controlled only by one program at once. Multiple
 * processes (programs) that control one device simultaneously are not allowed.
 *
 * \section sysreq_sec System requirements
 *
 * \subsection sysreq_build For rebuilding library
 *
 * On Windows:
 * - Windows 2000 or later, 64-bit system (if compiling both arhitectures) or 32-bit system. 
 * - Microsoft Visual C++ 2013 or later
 * - cygwin with tar, bison, flex, curl installed
 * - 7z
 *
 * On Linux:
 * - 64-bit or/and 32-bit system system
 * - gcc 4 or later
 * - common autotools: autoconf, autoheader, aclocal, automake, autoreconf, libtool
 * - gmake
 * - doxygen - for building docs
 * - LaTeX distribution (teTeX or texlive) - for building docs
 * - flex 2.5.30+
 * - bison
 * - mercurial (for building developer version from hg)
 *
 * On Mac OS X:
 * - XCode 4
 * - doxygen
 * - mactex
 * - autotools
 * - mercurial (for building developer version from hg)
 *
 * If mercurial is used, please enable 'purge' extension by adding to ~/.hgrc following lines:
 * \verbatim
   [extensions]
     hgext.purge=
   \endverbatim
 * 
 * \subsection sysreq_usage For using library
 *
 * Supported operating systems (32 or 64 bit) and environment requirements:
 * - Mac OS X 10.6
 * - Windows 2000 or later
 * - Autotools-compatible unix. Package is installed from sources.
 * - Linux debian-based 32 and 64 bit. DEB package is built against Debian Squeeze 7
 * - Linux debian-based ARM. DEB package is built on Ubuntu 14.04
 * - Linux rpm-based. RPM is built against OpenSUSE 12
 * - Java 7 64-bit or 32-bit
 * - .NET 2.0 (32-bit only)
 * - Delphi (32-bit only)
 
 *
 * Build requirements:
 * - Windows: Microsoft Visual C++ 2013 or mingw (currently not supported)
 * - UNIX: gcc 4, gmake
 * - Mac OS X: XCode 4
 * - JDK 7
 *
 *

 * \page building_sec How to rebuild library
 *

 * \section building_unix Building on generic UNIX
 *
 * Generic version could be built with standard autotools.
 * \code
 *   ./build.sh lib
 * \endcode
 * Built files (library, headers, documentation) are installed to ./dist/local directory.
 * It is a generic developer build. Sometimes you need to specify additional parameters to
 * command line for your machine. Please look to following OS sections.
 *
 * \section building_unix_deb Building on debian-based linux systems
 * Requirement: 64-bit and 32-bit debian system, ubuntu
 * Typical set of packages: gcc, autotools, autoconf, libtool, dpkg-dev, flex, bison, doxygen, texlive, mercurial
 * Full set of packages: apt-get install ruby1.9.1 debhelper vim sudo g++ mercurial git curl make cmake autotools-dev automake autoconf libtool default-jre-headless default-jdk openjdk-6-jdk dpkg-dev lintian texlive texlive-latex-extra texlive-lang-cyrillic dh-autoreconf hardening-wrapper bison flex doxygen lsb-release pkg-config check
 * For ARM cross-compiling install gcc-arm-linux-gnueabihf from your ARM toolchain.
 *
 * It's required to match library and host architecture: 64-bit library can be built only at 64-bit host,
 * 32-bit library - only at 32-bit host. ARM library is built with armhf cross-compiler gcc-arm-linux-gnueabihf.
 *
 * To build library and package invoke a script:
 * \code
 * $ ./build.sh libdeb
 * \endcode
 * 
 * For ARM library replace 'libdeb' with 'libdebarm'.
 *
 * Grab packages from ./ximc/deb and locally installed binaries from ./dist/local.
 *
 * \section building_unix_rpm Building on redhat-based linux systems
 * Requirement: 64-bit redhat-based system (Fedora, Red Hat, SUSE)
 * Typical set of packages: gcc, autotools, autoconf, libtool, flex, bison, doxygen, texlive, mercurial
 * Full set of packages: autoconf automake bison doxygen flex gcc gcc-32bit gcc-c++ gcc-c++-32bit java-1_7_0-openjdk java-1_7_0-openjdk-devel libtool lsb-release make mercurial rpm-build rpm-devel rpmlint texlive texlive-fonts-extra texlive-latex 
 *
 * It's possible to build both 32- and 64-bit libraries on 64-bit host system.
 * 64-bit library can't be built on 32-bit system.
 *
 * To build library and package invoke a script:
 * \code
 * $ ./build.sh librpm
 * \endcode
 * 
 * Grab packages from ./ximc/rpm and locally installed binaries from ./dist/local.
 *
 *
 * \section building_osx_generic Buliding on Mac OS X
 *
 * To build and package a script invoke a script:
 * \code
 * $ ./build.sh libosx
 * \endcode
 *
 * Built library (classical and framework), examples (classical and .app), documentation
 * are located at ./ximc/macosx, locally installed binaries from ./dist/local.
 *
 * \section building_win Buliding on Windows
 *
 * Requirements: 64-bit windows (build script builds both architectures), cygwin (must be installed to a default path), mercurial.
 *
 * Invoke a script:
 * \code
 * $ ./build.bat
 * \endcode
 *
 * Grab packages from ./deb/win32 and ./deb/win64 
 *
 * To build debug version of the library set environment variable "DEBUG" to "true" before running the build script.
 *
 * \section building_src Source code access
 * XIMC source codes are given under special request.
 *
 * \page howtouse_sec How to use with...
 *
 * Library usage can be examinated from test application testapp.
 * Non-C languages are supported because library supports stdcall calling convention and so can be used with a variety of languages.
 *
 * C test project is located at 'examples/testapp' directory, C# test project - at 'examples/testcs', VB.NET - 'examples/testvbnet', 
 * Delphi 6 - 'examples/testdelphi', sample bindings for MATLAB - 'examples/testmatlab', for Java - 'examples/testjava',
 * for Python - 'examples/testpython'.
 * Development kit also contains precompiled examples: testapp and testappeasy as 32 and 64-bit applications for Windows and 64-bit application for osx,
 * testcs, testvbnet, testdelphi - 32-bit only, testjava is architecture-independent, testmatlab and testpython are runtime-interpreted.
 *
 * NOTE: SDK requires Microsoft Visual C++ Redistributable Package (provided with SDK - vcredist_x86 or vcredist_x64)
 *
 * \section howtouse_c_sec Usage with C
 *
 * \subsection howtouse_c_vcpp_sec Visual C++
 *
 * Testapp can be built using testapp.sln. 
 * Library must be compiled with MS Visual C++ too, mingw-library isn't supported.
 * Make sure that Microsoft Visual C++ Redistributable Package is installed. 
 *
 * Open solution examples/testapp/testapp.sln, build and run from the IDE.
 *
 * \subsection howtouse_c_codeblocks CodeBlocks
 *
 * Testapp can be built using testcodeblocks.cbp. 
 * Library must be compiled with MS Visual C++ too, mingw-library isn't supported.
 * Make sure that Microsoft Visual C++ Redistributable Package is installed.  *
 *
 * Open solution examples/testcodeblocks/testcodeblocks.cbp, build and run from the IDE.
 *
 * \subsection howtouse_c_mingw_sec MinGW
 *
 * MinGW is a port of GCC to win32 platform.
 * It's required to install MinGW package.
 * Currently not supported
 *
 * MinGW-compiled testapp can be built with MS Visual C++ or mingw library.
 * \code
 * $ mingw32-make -f Makefile.mingw all
 * \endcode
 *
 * Then copy library libximc.dll to current directory and launch testapp.exe.
 *
 * \subsection howtouse_c_bcb_sec C++ Builder
 *
 * First of all you should create C++ Builder-style import library. Visual C++ library is not compatible with BCB.
 * Invoke:
 * \code
 * $ implib libximc.lib libximc.def
 * \endcode
 *
 * Then compile test application:
 * \code
 * $ bcc32 -I..\..\ximc\win32 -L..\..\ximc\win32 -DWIN32 -DNDEBUG -D_WINDOWS testapp.c libximc.lib
 * \endcode
 *
 * \subsection howtouse_c_xcode_sec XCode
 *
 * Test app should be built with XCode project testapp.xcodeproj. 
 * Library is a Mac OS X framework, and at example application it's bundled inside testapp.app
 *
 * Then launch application testapp.app and check activity output in Console.app.
 *
 * \subsection howtouse_c_gcc_sec GCC
 *
 * Make sure that libximc (rpm, deb, freebsd package or tarball) is installed at your system.
 * Installation of package should be performed with a package manager of operating system.
 * On OS X a framework is provided.
 *
 * Note that user should belong to system group which allows access to a serial port (dip or serial, for example).
 *
 * Copy file /usr/share/libximc/keyfile.sqlite project directory:
 * \code
 * $ cp /usr/share/libximc/keyfile.sqlite .
 * \endcode
 *
 * Test application can be built with the installed library with the following script:
 * \code
 * $ make
 * \endcode
 *
 * In case of cross-compilation (target architecture differs from the current system architecture)
 * feed -m64 or -m32 flag to compiler. On OS X it's needed to use -arch flag instead to build an universal binary.
 * Please consult a compiler documentation.
 *
 * Then launch the application as:
 * \code
 * $ make run
 * \endcode
 *
 * Note: make run on OS X copies a library to the current directory.
 * If you want to use library from
 * the custom directory please be sure to specify LD_LIBRARY_PATH or DYLD_LIBRARY_PATH to
 * the directory with the library. 
 *
 * \section howtouse_dotnet_sec .NET
 * 
 * Wrapper assembly for libximc.dll is wrappers/csharp/ximcnet.dll.
 * It is provided with two different architectures and depends on .NET 2.0.
 *
 * Test .NET applications for Visual Studio 2013 is located at testcs (for C#) and testvbnet (for VB.NET) respectively.
 * Open solutions and build.
 *
 * \section howtouse_delphi_sec Delphi
 *
 * Wrapper for libximc.dll is a unit wrappers/delphi/ximc.pas
 *
 * Console test application for is located at testdelphi. Tested with Delphi 6 and only 32-bit version.
 *
 * Just compile, place DLL near the executable and run program.
 *
 * \section howtouse_java_sec Java
 *
 * How to run example on Linux. Navigate to ximc-2.x.x./examples/testjava/compiled/ and run:
 * \code
 * $ cp /usr/share/libximc/keyfile.sqlite .
 * $ java -cp /usr/share/java/libjximc.jar:testjava.jar ru.ximc.TestJava
 * \endcode
 *
 * How to run example on Windows or Mac. Navigate to ximc-2.x.x./examples/testjava/compiled/.
 * Copy contents of ximc-2.x.x/ximc/win64 or ximc-2.x.x/ximc/macosx accordingly to the current directory.
 * Then run:
 * \code
 * $ java -classpath libjximc.jar -classpath testjava.jar ru.ximc.TestJava
 * \endcode
 
 * How to modify and recompile an example.
 * Navigate to examples/testjava/compiled. Sources are embedded in a testjava.jar.
 * Extract them:
 * \code
 * $ jar xvf testjava.jar ru META-INF
 * \endcode
 * Then rebuild sources:
 * \code
 * $ javac -classpath /usr/share/java/libjximc.jar -Xlint ru/ximc/TestJava.java
 * \endcode
 * or for windows or mac
 * \code
 * $ javac -classpath libjximc.jar -Xlint ru/ximc/TestJava.java
 * \endcode
 * Then build a jar:
 * \code
 * $ jar cmf META-INF/MANIFEST.MF testjava.jar ru
 * \endcode
 *
 * \section howtouse_python_sec Python
 *
 * Change current directory to the examples/testpython.
 *
 * Before launch:
 *
 * On OS X: copy library ximc/macosx/libximc.framework to the current directory.
 *
 * On Linux: you may need to set LD_LIBRARY_PATH 
 * so Python can locate libraries with RPATH. For example, you may need:
 * \code
 * export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:`pwd`
 * \endcode
 *
 * On Windows before the start nothing needs to be done
 *
 * Launch Python 2 or Python 3:
 * \code
 * python testpython.py
 * \endcode
 *
 * \section howtouse_matlab_sec MATLAB
 *
 * Sample MATLAB program testximc.m is provided at the directory examples/testmatlab.
 * On windows copy ximc.h, libximc.dll, bindy.dll, xiwrapper.dll and contents of ximc/(win32,win64)/wrappers/matlab/ directory to the current directory.
 *
 * Before launch:
 *
 * On OS X: copy ximc/macosx/libximc.framework, ximc/macosx/wrappers/ximcm.h,
 * ximc/ximc.h * to the directory examples/matlab. Install XCode compatible with Matlab.
 *
 * On Linux: install libximc*deb and libximc-dev*dev of target architecture.
 * Then copy ximc/macosx/wrappers/ximcm.h to the directory examples/matlab. Install gcc compatible with Matlab.
 *
 * For XCode and gcc version compability check document 
 * https://www.mathworks.com/content/dam/mathworks/mathworks-dot-com/support/sysreq/files/SystemRequirements-Release2014a_SupportedCompilers.pdf or similar.
 *
 * On Windows before the start nothing needs to be done
 *
 * Change current directory in the MATLAB to the examples/matlab.
 * Then launch in MATLAB prompt:
 * \code
 * testximc
 * \endcode
 *
 * \section howtouse_log Generic logging facility
 *
 * If you want to turn on file logging, you should run the program that uses libximc library with the "XILOG" environment variable set to desired file name.
 * This file will be opened for writing on the first log event and will be closed when the program which uses libximc terminates.
 * Data which is sent to/received from the controller is logged along with port open and close events.
 *
 * \section howtouse_perm Required permissions
 *
 * libximc generally does not require special permissions to work, it only needs read/write access to USB-serial ports on the system.
 * An exception to this rule is a Windows-only "fix_usbser_sys()" function - it needs elevation and will produce null result if run as a regular user.
 *
 * \section howtouse_cprofiles C-profiles
 * 
 * C-profiles are header files distributed with the libximc library. They enable one to set all controller settings for any of the supported stages with a single function call in a C/C++ program.
 * You may see how to use C-profiles in "testcprofile" example directory.
 * 
 * 
 */
