# Development stage
FROM node:22-alpine AS development
RUN apk upgrade --no-cache
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Build stage — always on the native builder arch.
# Cross-compiling Node/npm under QEMU for linux/arm64 crashes with
# "qemu: uncaught target signal 4 (Illegal instruction)". Vite output is
# architecture-independent static files, so building on $BUILDPLATFORM is safe.
FROM --platform=$BUILDPLATFORM node:22-alpine AS build
RUN apk upgrade --no-cache
WORKDIR /app
COPY package*.json ./
RUN npm ci --include=dev
COPY . .
RUN npm run build

# Production stage — static assets only (no Node/npm runtime)
FROM nginx:alpine AS production
RUN apk upgrade --no-cache
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
