FROM python:3.9.18-slim

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY main.py main.py

EXPOSE 8002

# uvicorn main:app --host 0.0.0.0 --port 8002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]