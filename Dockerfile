FROM python:3.13-slim

WORKDIR /app

COPY requirements/production.txt requirements/production.txt
COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/production.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=sigra.settings.production

CMD ["gunicorn", "sigra.wsgi:application", "--bind", "0.0.0.0:8000"]
