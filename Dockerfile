FROM python:3.14-slim

RUN useradd --create-home --uid 1000 appuser
WORKDIR /home/appuser/app
# WORKDIR creates the folder as root; the build step below writes data/ and prepared/ in it as appuser
RUN chown appuser:appuser /home/appuser/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser app.py ./
COPY --chown=appuser dashboard ./dashboard
COPY --chown=appuser pages ./pages
COPY --chown=appuser assets ./assets

USER appuser
# Download, aggregate and check the EUROCONTROL files at build time, so start-up only reads the result.
# The downloaded files are removed afterwards; the data is never stored in the repository.
# To get new data without a code change, rebuild without the build cache.
ENV PREPARED_FILE=prepared/dataset.pkl
RUN python -m dashboard.prepare && rm -rf data

# The hosting platform may set PORT; 10000 is used otherwise.
# One worker (a 0.1 CPU, 512 MB instance) with threads for parallel requests.
ENV PORT=10000
EXPOSE 10000
CMD ["sh", "-c", "gunicorn app:server --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120"]
