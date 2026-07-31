FROM python:3.11-slim

WORKDIR /app

# app.py butuh src/ & dataset/ sebagai sibling folder (dia sys.path.append
# dirname-of-dirname dirinya sendiri), jadi struktur di image harus sama
# persis dengan repo: /app/api, /app/src, /app/dataset.
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY api api
COPY src src
COPY dataset dataset

EXPOSE 5001

CMD ["python", "api/app.py"]
