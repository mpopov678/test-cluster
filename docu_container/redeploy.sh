#!/bin/bash

# pull from repo when webhook triggers, rebuild html files, and copy to shared volume for caddy
cd /quartz
git -C /quartz/content pull
npx quartz build --port 8080
cp -r public/* shared/