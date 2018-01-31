FROM node:9.4.0

COPY ./package.json /var/www/package.json
RUN npm install

WORKDIR /var/www
