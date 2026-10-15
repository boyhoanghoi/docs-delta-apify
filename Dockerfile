FROM apify/actor-python:3.13
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir '.[actor]'
CMD ["python", "-m", "docsdelta.actor"]
