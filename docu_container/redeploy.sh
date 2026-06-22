#!/bin/bash

# Sends echo output to primary console stream of container
echo "==================" > /proc/1/fd/1
echo "Webhook triggered!" > /proc/1/fd/1
echo "==================" > /proc/1/fd/1

# pull from repo when webhook triggers, rebuild html files, and copy to shared volume for caddy
cd /quartz
git -C /quartz/content pull
npx quartz build --port 8080
rsync --delete --recursive public/ shared/