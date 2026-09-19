FROM mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04:latest

COPY conda.yml /tmp/conda.yml
RUN conda env update -n base -f /tmp/conda.yml && conda clean -afy

# Immutable — this image is referenced by digest, never `latest`, from every
# training job and deployment so "which exact image served model v6" is never
# a guess during an incident.
