# ================================================
# 前端 Dockerfile - Vue 3 + Vite
# ================================================

ARG NODE_IMAGE=docker.m.daocloud.io/library/node:20-alpine3.22
FROM ${NODE_IMAGE} AS builder

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

RUN npx vite build

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
