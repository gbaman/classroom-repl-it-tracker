
FROM python:latest
EXPOSE 8000

# Install needed libraries
RUN mkdir /app
COPY requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt
RUN pip3 install gunicorn

# Copy app code over
COPY . /app
WORKDIR /app

# Run Gunicorn with the log file
CMD ["/usr/local/bin/gunicorn", "-w", "2", "-t", "60", "-b", ":8000", "--log-file", "/var/repl/app.log", "--capture-output", "app:app"]