# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.8.11@sha256:8101ad825250a114e7bef89eefaa73c31e34e10ffbe5aff01562740bac97553c AS uv
FROM python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

ARG DEBIAN_FRONTEND=noninteractive

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONHASHSEED=0 \
    MPLBACKEND=Agg \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/flagella-venv

COPY --from=uv /uv /uvx /usr/local/bin/

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        fonts-dejavu-core \
        fonts-liberation \
        libcairo2 \
        libfreetype6 \
        libgomp1 \
        libjpeg62-turbo \
        libopenblas0 \
        libpng16-16 \
        libtiff6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --all-groups

COPY . .
RUN uv sync --frozen --all-groups --no-editable \
    && python -c "import flagella_repro; print(flagella_repro.__file__)" \
    && useradd --create-home --uid 10001 reproducibility \
    && chown -R reproducibility:reproducibility /workspace /opt/flagella-venv

USER reproducibility
ENV PATH="/opt/flagella-venv/bin:${PATH}"

CMD ["python", "--version"]
