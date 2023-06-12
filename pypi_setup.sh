#!/bin/sh

folder1="./build"
folder2="./dist"
folder3="./vosk_autosrt.egg-info"

if [ -d "$folder1" ]; then
	rm -rf "$folder1"
fi

if [ -d "$folder2" ]; then
	rm -rf "$folder2"
fi

if [ -d "$folder3" ]; then
	rm -rf "$folder3"
fi

python3.8 setup.py sdist
python3.8 setup.py bdist_wheel --plat-name manylinux_2_17_x86_64
