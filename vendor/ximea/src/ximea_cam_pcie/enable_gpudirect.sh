#!/bin/bash
function Check() {
	if [ $? == 0 ]
	then
		echo "OK"
	else
		echo "Error on previous command"
		exit 1
	fi
}

cd "$(dirname "$0")"
KERNEL="${KERNEL:-$(uname -r)}"
NV_VERSION="${NV_VERSION:-$(modinfo -k "$KERNEL" -F version "$(modprobe -R nvidia)")}"
if [ -z "$NV_VERSION" ]
then
	echo "NVIDIA drivers are not installed!!!"
	exit 1
fi
if [ ! -d "NVIDIA-Linux-x86_64-$NV_VERSION" ]
then
	echo "Downloading NVIDIA drivers package"
	curl -fLO "http://us.download.nvidia.com/XFree86/Linux-x86_64/$NV_VERSION/NVIDIA-Linux-x86_64-$NV_VERSION.run"
	Check
	chmod a+x "NVIDIA-Linux-x86_64-$NV_VERSION.run"
	./NVIDIA-Linux-x86_64-$NV_VERSION.run -x
	Check
fi
echo "Copying nv-p2p.h"
find "NVIDIA-Linux-x86_64-$NV_VERSION" -name nv-p2p.h -exec cp '{}' . \;
Check
make clean
echo "Generating Module.symvers"
pushd "NVIDIA-Linux-x86_64-$NV_VERSION"/kernel
make clean
make KERNEL="$KERNEL" module
Check
popd
cp "NVIDIA-Linux-x86_64-$NV_VERSION"/kernel/Module.symvers .
Check
echo "Rebuilding ximea_cam_pcie kernel module"
make KERNEL="$KERNEL" GPUDIRECT=1
Check
echo "Installing ximea_cam_pcie kernel module"
make KERNEL="$KERNEL" install
Check
depmod "$KERNEL"
Check
if [ "$KERNEL" = "$(uname -r)" ]
then
	echo "Reloading ximea_cam_pcie kernel module, will fail if it is in use"
	rmmod ximea_cam_pcie 2>/dev/null
	modprobe --first-time ximea_cam_pcie
	Check
fi
