FROM node:22-slim AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# busybox wget (bundled with nginx:alpine) rather than curl, which this
# image doesn't otherwise need — checks nginx itself is up and serving the
# built SPA, independent of the `api` service's own healthcheck.
#
# `127.0.0.1`, not `localhost`: this image's /etc/hosts resolves
# `localhost` to both 127.0.0.1 and ::1, nginx only binds IPv4, and
# busybox wget's first attempt lands on ::1 — "connection refused" even
# though the server is up (found by actually running this healthcheck).
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1
