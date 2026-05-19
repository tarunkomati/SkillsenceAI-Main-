FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY src ./src
COPY public ./public
COPY index.html vite.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json postcss.config.js tailwind.config.ts components.json eslint.config.js ./
RUN npm run build

FROM python:3.13-slim AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .
COPY --from=frontend-builder /app/dist ./dist

# Collect static assets during image build so the runtime only has to start the app.
ENV DJANGO_DEBUG=false \
    DJANGO_SECRET_KEY=build-time-only-secret \
    DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
    DATABASE_URL=sqlite:///build.db

RUN python manage.py collectstatic --noinput

RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
