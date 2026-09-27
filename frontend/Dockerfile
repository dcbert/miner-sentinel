# Development stage
FROM node:22-alpine AS development
RUN apk upgrade --no-cache \
    && npm install -g npm@latest
WORKDIR /app
COPY package*.json ./
RUN npm i
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Build stage
FROM node:22-alpine AS build
RUN apk upgrade --no-cache \
    && npm install -g npm@latest
WORKDIR /app
COPY package*.json ./
RUN npm i --include=dev
COPY . .
RUN npm run build

# Production stage — static assets only (no Node/npm runtime)
FROM nginx:alpine AS production
RUN apk upgrade --no-cache
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
