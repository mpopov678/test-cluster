#!/bin/sh

# install dependencies and initialize quartz
cd /quartz
npm i
npx quartz create -t default -X new -s /docu -l shortest -b docu.lab.mpopov.net

# create env variable using mounted secret and clone private repo into content/
PAT=$(cat secret/token)
rm -rf content
git clone https://gitlab-token:${PAT}@gitlab.lab.mpopov.net/root/docs.git content
# build html files and copy to shared volume
npx quartz build --port 8080
cp -r public/* shared/

cd /usr/src/app
# start webhook service on default port 9000 with one http endpoint 
webhook -hooks hooks.json
