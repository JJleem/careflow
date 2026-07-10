# 1단계: 빌드 — node로 정적 파일(dist) 생성
FROM node:22-alpine AS build
WORKDIR /app

# 의존성 레이어 분리: 소스만 바뀌면 npm ci를 다시 하지 않도록 (빌드 캐시)
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# 2단계: 서빙 — nginx가 정적 파일을 제공하고 /api를 backend로 프록시
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
