FROM node:26

RUN git clone https://github.com/jackyzha0/quartz.git 
WORKDIR /quartz 
RUN npm i
RUN npx quartz create -t default -X new -s /docu -l shortest -b docu.lab.mpopov.net

COPY test.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]