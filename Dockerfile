# Dockerfile
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /workspace

# Evita que Python almacene archivos .pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copia los archivos necesarios para instalar dependencias primero
COPY requirements.txt ./

# Instala dependencias de Python
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["bash", "-c", "if [ ! -f manage.py ]; then django-admin startproject financiera . ; fi && python manage.py runserver 0.0.0.0:8000"]
