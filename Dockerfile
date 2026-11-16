FROM python:3.12-slim
WORKDIR /project
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["sh", "-c", "python manage.py init && gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 2 --access-logfile - 'app:create_app()'"]
