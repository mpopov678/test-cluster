#!/bin/sh

cd /quartz
rm -rf content
git clone https://github.com/mpopov678/docu.git content

while true; do
    git -C /quartz/content pull
    npx quartz build --port 8080
    cp -r public/* shared/
    sleep 300
done