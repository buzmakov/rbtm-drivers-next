/*!
 * \mainpage Библиотека libximc
 *
 * Документация для библиотеки libximc.
 *
 * \image html logo.png
 *
 * Libximc - кроссплатформенная библиотека для работы с контроллерами ximc 8SMC4 и 8SMC5.
 *
 * Полная документация по контроллерам ximc доступна по <a href="https://doc.xisupport.com">ссылке</a>
 *
 * Полная документация по API libximc доступна на странице \ref ximc.h.
 * 
 * \section about_ximc О продукте ximc
 *
 * Мы предлагаем недорогой ультра-компактный сервопривод с интерфейсом USB для шаговых двигателей с внешним питанием.
 * Забудьте о громоздких и дорогих сервоприводах! Теперь для работы вам понадобятся: шаговый двигатель, контроллер, USB кабель и практически любой внешний стабилизированный источник питания. И все! Не нужно никакого активного охлаждения. Плата контроллера по размеру не превосходит блокнот или сотовый телефон, так что вы можете положить его прямо на рабочий стол, не прибегая к монтажу. Контроллер может работать со всеми компактными шаговыми двигателями с током обмотки до 3 А, без обратной связи, а так же с шаговыми двигателями, оснащенными энкодером в цепи обратной связи, в том числе линейным энкодером на позиционере. Разъем для мотора на контроллере соответствует разъему, который использует компания Standa, и подходит для всех позиционеров Standa. USB соединение обеспечивает легкость подключения и простоту работы с компьютером. Несколько контроллеров могут быть подключены к одному компьютеру через несколько USB-портов или с помощью специальной объединительной платы, поставляемой в составе многоосных систем. Контроллер совместим практически со всеми операционными системами (Windows, Mac OS X, Linux и т. д.).
 *
 * \section about_libximc О продукте libximc
 *
 * Спасибо, что вы выбрали мультиплатформенную библиотеку XIMC! Этот документ содержит всю необходимую информацию о библиотеке XIMC. 
 * Она использует распространенный и проверенный интерфейс виртуального последовательного порта, поэтому вы можете работать с модулями управления моторами через эту библиотеку практически под всеми под ОС, в том числе Windows 7, Windows Vista, Windows XP, Windows Server 2003, Windows 2000, Linux, Mac OS X. 
 * Библиотека XIMC поддерживает подключение и отключение устройств "на лету". 
 * C одним устройством в каждый момент может работать не более одного экземпляра управляющей программы -
 * множественный доступ управляющих программ к одному и тому же устройству не допускается.
 *
 * Пожалуйста, прочитайтие \ref intro_sec для начала работы с библиотекой.
 *
 * Для того, чтобы использовать libximc в проекте, ознакомьтесь со страницей \ref howtouse_sec
 *
 * \page intro_sec Введение
 *
 * \section about_sec О библиотеке
 *
 * Спасибо, что вы выбрали мультиплатформенную библиотеку XIMC! Этот документ содержит всю необходимую информацию о библиотеке XIMC. 
 * Она использует распространенный и проверенный интерфейс виртуального последовательного порта, поэтому вы можете работать с модулями управления моторами через эту библиотеку практически под всеми под ОС, в том числе Windows 7, Windows Vista, Windows XP, Windows Server 2003, Windows 2000, Linux, Mac OS X. 
 * Библиотека XIMC поддерживает подключение и отключение устройств "на лету". 
 * C одним устройством в каждый момент может работать не более одного экземпляра управляющей программы -
 * множественный доступ управляющих программ к одному и тому же устройству не допускается.
 *
 * \section sysreq_sec Требования к установленному программному обеспечению
 *
 * \subsection sysreq_build Для сборки библиотеки
 *
 * Для Windows:
 * - Windows 2000 или старше, 64-битная система (если планируется собирать обе архитектуры) или 32-битная система
 * - Microsoft Visual C++ 2013 или старше
 * - cygwin с tar, bison, flex, curl
 * - 7z
 *
 * Для Linux:
 * - 64-битная и/или 32-битная система
 * - gcc 4 или новее
 * - стандартные autotools: autoconf, autoheader, aclocal, automake, autoreconf, libtool
 * - gmake
 * - doxygen - для сборки документации
 * - LaTeX distribution (teTeX or texlive) - для сборки документации
 * - flex 2.5.30+
 * - bison
 * - mercurial (для сборки версии для разработки из hg)
 *
 * Для Mac OS X:
 * - XCode 4
 * - doxygen
 * - mactex
 * - autotools
 * - mercurial (для сборки версии для разработки из hg)
 *
 * Для зависимость от mercurial.
 * При использовании mercurial включите расширение 'purge' путем добавления в ~/.hgrc следующих строк:
 * \verbatim
   [extensions]
     hgext.purge=
   \endverbatim
 *
 * \subsection sysreq_usage Для использования библиотеки
 *
 * Поддерживаемые операционные системы (32 и 64 бита) и требования к окружению:
 * - Mac OS X 10.6
 * - Windows 2000 или старше
 * - Autotools-совместимый unix. Библиотека устанавливается из бинарного вида.
 * - Linux на основе debian 32 и 64 бита. DEB собирается на Debian Squeeze 7
 * - Linux на основе debian ARM. DEB собирается кросс-компилятором на Ubuntu 14.04
 * - Linux на основе rpm. RPM собирается на OpenSUSE 12
 * - Java 7 64 бит или 32 бит
 * - .NET 2.0 (только 32 бит)
 * - Delphi (только 32 бит)
 *
 * Требования сборки:
 * - Windows: Microsoft Visual C++ 2013 или mingw (в данный момент не поддерживается)
 * - UNIX: gcc 4, gmake
 * - Mac OS X: XCode 4
 * - JDK 7
 *
 * \page building_sec Как пересобрать библиотеку
 *
 *
 * \section building_unix Сборка для UNIX
 *
 * Обобщенная версия собирается обычными autotools.
 * \code
 *   ./build.sh lib
 * \endcode
 * Собранные файлы (библиотека, заголовочные файлы, документация) устанавливаются в локальную директорию  ./dist/local.
 * Это билд для разработчика. Иногда необходимо указать дополнительные параметры командной строки для вашей системы.
 * Проконсультируйтесь с последующими параграфами.
 *
 * \section building_unix_deb Сборка для Linux на основе Debian
 * Требования: 64-битная или 32-битная система на основе debian, ubuntu
 * Примерный набор пакетов: gcc, autotools, autoconf, libtool, dpkg-dev, flex, bison, doxygen, texlive, mercurial
 * Полный набор пакетов: apt-get install ruby1.9.1 debhelper vim sudo g++ mercurial git curl make cmake autotools-dev automake autoconf libtool default-jre-headless default-jdk openjdk-6-jdk dpkg-dev lintian texlive texlive-latex-extra texlive-lang-cyrillic dh-autoreconf hardening-wrapper bison flex doxygen lsb-release pkg-config check
 * Для кросс-компиляции ARM установите gcc-arm-linux-gnueabihf из вашего инструментария ARM.
 *
 * Необходимо соблюдать парность архитектуры библиотеки и системы: 64-битная библиотека может быть собрана только на 64-битной системе,
 * а 32-битная - только на 32-битной. Библиотека под ARM собирается кросс-компилятором gcc-arm-linux-gnueabihf.
 *
 * Для сборки библиотеки и пакета запустите скрипт:
 * \code
 * $ ./build.sh libdeb
 * \endcode
 * 
 * Для библиотеки ARM замените 'libdeb' на 'libdebarm'.
 *
 * Пакеты располагаются в ./ximc/deb, локально инсталированные файлы в ./dist/local.
 *
 * \section building_unix_rpm Сборка для Linux на основе RedHat
 * Требования: 64-битная система на основе redhat (Fedora, Red Hat, SUSE)

 * Примерный набор пакетов: gcc, autotools, autoconf, libtool, flex, bison, doxygen, texlive, mercurial 
 * Полный набор пакетов: autoconf automake bison doxygen flex gcc gcc-32bit gcc-c++ gcc-c++-32bit java-1_7_0-openjdk java-1_7_0-openjdk-devel libtool lsb-release make mercurial rpm-build rpm-devel rpmlint texlive texlive-fonts-extra texlive-latex 
 *
 * Возможно собрать 32-битную и 64-битную библиотеки на 64-битной системе, однако 64-битная
 * библиотека не может быть собрана на 32-битной системе.
 *
 * Для сборки библиотеки и пакета запустите скрипт:
 * \code
 * $ ./build.sh librpm
 * \endcode
 * 
 * Пакеты располагаются в ./ximc/rpm, локально инсталированные файлы в ./dist/local.
 *
 * \section building_osx_framework Сборка для Mac OS X
 *
 * Для сборки библиотеки и пакета запустите скрипт:
 * \code
 * $ ./build.sh libosx
 * \endcode
 *
 * Собранная библиотека (классическая и фреймворк), приложения (классическая и фреймворк) и документация
 * располашаются в ./ximc/macosx, локально инсталированные файлы в ./dist/local.
 *
 * \section building_win Сборка в ОС Windows
 *
 * Требования: 64-битный windows (сборочный скрипт собирает обе архитектуры), cygwin (должен быть установлен в
 * пути по умолчанию), mercurial.
 * 
 * Запустите скрипт:
 * \code
 * $ ./build.bat
 * \endcode
 * 
 * Собранные файлы располагаются в ./ximc/win32 и ./ximc/win64
 *
 * Если вы хотите собрать дебаг-версию библиотеки, то перед запуском скрипта сборки установите переменную окружения "DEBUG" в значение "true".
 *
 * \section building_src Доступ к исходным кодам
 * Исходные коды XIMC могут быть выданы по отдельному запросу.
 *
 * \page howtouse_sec Как использовать с...
 *
 * Для приобретения первых навыков использования библиотеки создано простое тестовое приложение testapp. 
 * Языки, отличные от C-подобных, поддерживаются с помощью вызовов с преобразованием аргументов типа stdcall.
 * Простое тестовое приложение на языке C расположено в директории 'examples/testapp', проект на C# - в 'examples/testcs', 
 * на VB.NET - в 'examples/testvbnet', для delphi 6 - в 'example/testdelphi', для matlab - 'examples/testmatlab',
 * для Java - 'examples/testjava', для Python - 'examples/testpython'.
 * Библиотеки, заголовочные файлы и другие необходимые файлы расположены в директориях 'win32'/'win64','macosx' и подобных.
 * В комплект разработчика также входят уже скомпилированные примеры: testapp и testappeasy в варианте 32 и 64 бита под windows и только 64 бита под osx,
 * testcs, testvbnet, testdelphi - только 32 бита, testjava - кроссплатформенный, testmatlab и testpython не требуют компиляции.
 *
 * ЗАМЕЧАНИЕ: Для работы с SDK требуется Microsoft Visual C++ Redistributable Package (поставляется с SDK, файлы vcredist_x86 или vcredist_x64).
 *
 * \section howtouse_c_sec Использование на C
 *
 * \subsection howtouse_c_vcpp_sec Visual C++
 *
 * Тестовое приложение может быть собрано с помощью testapp.sln. 
 * Для компиляции необходимо использовать также MS Visual C++, mingw-library не поддерживается. 
 * Убедитесь, что Microsoft Visual C++ Redistributable Package установлен.
 *
 * 
 * Откройте проект examples/testapp/testapp.sln, выполните сборку и запустите приложение из среды разработки.
 *
 * \subsection howtouse_c_codeblocks CodeBlocks
 *
 * Тестовое приложение может быть собрано с помощью testcodeblocks.cbp
 * Для компиляции необходимо использовать также MS Visual C++, mingw-library не поддерживается. 
 * Убедитесь, что Microsoft Visual C++ Redistributable Package установлен.
 *
 *
 * Откройте проект examples/testcodeblocks/testcodeblocks.cbp, выполните сборку и запустите приложение из среды разработки.
 *
 * \subsection howtouse_c_mingw_sec MinGW
 *
 * MinGW это вариант GCC для платформы win32. Требует установки пакета MinGW.
 * В данный момент не поддерживается.
 *
 * testapp, скомпилированный с помощью MinGW, может быть собран с MS Visual C++ или библиотеками mingw:
 * \code
 * $ mingw32-make -f Makefile.mingw all
 * \endcode
 *
 * Далее скопируйте libximc.dll в текущую директорию и запустите testapp.exe.
 *
 * \subsection howtouse_c_bcb_sec C++ Builder
 *
 * В первую очередь вы должны создать подходящую для C++ Builder библиотеку. Библиотеки Visual C++ и Builder не совместимы. 
 * Выполните: 
 * \code
 * $ implib libximc.lib libximc.def
 * \endcode
 *
 * Затем скомпилируйте тестовое приложение:
 * \code
 * $ bcc32 -I..\..\ximc\win32 -L..\..\ximc\win32 -DWIN32 -DNDEBUG -D_WINDOWS testapp.c libximc.lib
 * \endcode
 *
 * \subsection howtouse_c_xcode_sec XCode
 *
 * Test app должен быть собран проектом XCode testapp.xcodeproj. Используйте конфигурацию Release.
 * Библиотека поставляется в формате Mac OS X framework, в той же директории находится собранное тестовое приложение testapp.app.
 *
 * Запустите приложение testapp.app проверьте его работу в Console.app.
 *
 * \subsection howtouse_c_gcc_sec GCC
 *
 * Убедитесь, что libximc (с помощью rpm, deb или тарболла) установлена на вашей системе. 
 * Пакеты должны устанавливаться с помощью package manager'а вашей ОС.
 * Для OS X предоставляется фреймворк.
 *
 * Убедитесь, что пользователь принадлежит к группе, позволяющей доступ к COM-порту (например, dip или serial).
 *
 * Скопируйте файл /usr/share/libximc/keyfile.sqlite в директорию с проектом командой
 * \code
 * $ cp /usr/share/libximc/keyfile.sqlite .
 * \endcode
 *
 * testapp может быть собран следующим образом с установленной библиотекой:
 * \code
 * $ make
 * \endcode
 *
 * Для кросс-компиляции (архитектура целевой системы отличается от архитектуры хоста) следует передать флаг -m64 или -m32
 * компилятору. Для сборки universal binary на Mac OS X необходимо использовать вместо этого флаг -arch. 
 * Обратитесь к документации компилятора.
 *
 * Затем запустите приложение с помощью:
 * \code
 * $ make run
 * \endcode
 *
 * Примечание: make run на OS X копирует библиотеку в текущую директорию. 
 * Если вы хотите использовать библиотеку из другой директории, пожалуйста укажите в LD_LIBRARY_PATH или DYLD_LIBRARY_PATH 
 * путь к директории с библиотекой.
 *
 * \section howtouse_dotnet_sec .NET
 * 
 * Для использования в .NET предлагается обертка wrappers/csharp/ximcnet.dll.
 * Она распространяется в двух различных архитектурах и зависит от .NET 2.0.
 *
 * Тестовые приложения на языке C# для Visual Studio 2013 расположены в директориях testcs (для C#) и testvbnet (для VB.NET).
 * Откройте проекты и соберите.
 *
 * \section howtouse_delphi_sec Delphi
 *
 * Обертка для использования в Delphi libximc.dll предлагается как модуль wrappers/pascal/ximc.pas
 *
 * Консольное тестовое приложение размещено в директории 'testdelphi'. Проверено с Delphi 6 на 32-битной системе.
 *
 * Просто скомпилируйте, разместите DLL в директории с исполняемым модулем и запустите его.
 *
 * \section howtouse_java_sec Java
 *
 * Как запустить пример на Linux. Перейдите в ximc-2.x.x/examples/testjava/compiled/ и выполните
 * \code
 * $ cp /usr/share/libximc/keyfile.sqlite .
 * $ java -cp /usr/share/java/libjximc.jar:testjava.jar ru.ximc.TestJava
 * \endcode
 *
 * Как запустить пример на Windows или Mac. Перейдите в ximc-2.x.x./examples/testjava/compiled/.
 * Скопируйте содержимое ximc-2.x.x/ximc/win64/ или ximc-2.x.x/ximc/macosx/ соответственно
 * в текущую директорию. Затем запустите:
 * \code
 * $ java -classpath libjximc.jar -classpath testjava.jar ru.ximc.TestJava
 * \endcode
 *
 * Как модифицировать и пересобрать пример.
 * Исходный текст расположен внутри testjava.jar. Перейдите в examples/testjava/compiled.
 * Распакуйте jar:
 * \code
 * $ jar xvf testjava.jar ru META-INF
 * \endcode
 * Затем пересоберите исходные тексты:
 * \code
 * $ javac -classpath /usr/share/java/libjximc.jar -Xlint ru/ximc/TestJava.java
 * \endcode
 * или для Windows или Mac:
 * \code
 * $ javac -classpath libjximc.jar -Xlint ru/ximc/TestJava.java
 * \endcode
 * Затем соберите jar:
 * \code
 * $ jar cmf MANIFEST.MF testjava.jar ru
 * \endcode
 *
 *
 * \section howtouse_python_sec Python
 *
 * Измените текущую директорию на examples/testpython.
 *
 * Перед запуском:
 *
 * На OS X: скопируйте библиотеку ximc/macosx/libximc.framework в текущую директорию.
 *
 * На Linux: может понадобиться установить LD_LIBRARY_PATH, чтобы Python мог найти библиотеки с RPATH.
 * Например, запустите:
 * \code
 * export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:`pwd`
 * \endcode
 *
 * На Windows: перед запуском ничего делать не нужно
 *
 * Запустите Python 2 или Python 3:
 * \code
 * python testpython.py
 * \endcode
 *
 * \section howtouse_matlab_sec MATLAB
 *
 * Тестовая программа на MATLAB testximc.m располагается в директории examples/testmatlab.
 *
 * Перед запуском:
 *
 * На OS X: скопируйте ximc/macosx/libximc.framework, ximc/macosx/wrappers/ximcm.h,
 * ximc/ximc.h в директорию examples/matlab. Установите XCode, совместимый с Matlab
 *
 * На Linux: установите libximc*deb и libximc-dev*deb нужной архитектуры.
 * Далее скопируйте ximc/macosx/wrappers/ximcm.h в директорию examples/matlab. Установите gcc, совместимый с Matlab.
 *
 * Для проверки совместимых XCode и gcc проверьте документы
 * https://www.mathworks.com/content/dam/mathworks/mathworks-dot-com/support/sysreq/files/SystemRequirements-Release2014a_SupportedCompilers.pdf или похожие.
 *
 * На Windows: перед запуском ничего делать не нужно
 *
 * Измените текущую директорию в MATLAB на examples/matlab.
 * Затем запустите в MATLAB:
 * \code
 * testximc
 * \endcode
 *
 * \section howtouse_log Логирование в файл
 *
 * Если программа, использующая libximc, запущена с установленной переменной окружения XILOG, то это включит логирование в файл.
 * Значение переменной XILOG будет использовано как имя файла. Файл будет открыт на запись при первом событии лога и закрыт при завершении программы, использующей libximc.
 * В лог записываются события отправки данных в контроллер и приема данных из контроллера, а также открытия и закрытия порта.
 *
 * \section howtouse_perm Требуемые права доступа
 *
 * Библиотеке не требуются особые права для выполнения, а нужен только доступ на чтение-запись в USB-COM устройства в системе.
 * Исключением из этого правила является функция только для ОС Windows "fix_usbser_sys()" - если процесс использующий библиотеку
 * не имеет повышенных прав, то при вызове этой функции программная переустановка устройства не будет работать.
 *
 * \section howtouse_cprofiles Си-профили
 *
 * Си-профили это набор заголовочных файлов, распространяемых вместе с библиотекой libximc. Они позволяют в программе на языке C/C++ загрузить в контроллер настройки одной из поддерживаемых подвижек вызовом всего одной функции.
 * Пример использования си-профилей вы можете посмотреть в директории примеров "testcprofile".
 *
 *
 */
