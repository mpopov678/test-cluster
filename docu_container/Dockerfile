FROM node:26

RUN apt-get update && apt-get install -y webhook && apt-get install -y rsync

WORKDIR /usr/src/app

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

COPY hooks.json .

COPY redeploy.sh .
RUN chmod +x redeploy.sh

RUN git clone https://github.com/jackyzha0/quartz.git /quartz

ENTRYPOINT ["./entrypoint.sh"]