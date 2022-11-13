FROM node:lts-slim
ENV NODE_ENV=production
ENV DOCKER=true
ENV TITLE=Game\ Server

RUN apt-get update && apt-get install -y python3 build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY src/. .
COPY src/. /app.defaults

RUN npm install --production

EXPOSE 80/tcp

CMD [ "node", "server.js" ]
