FROM nvcr.io/nvidia/isaac-sim:6.1.0

RUN /isaac-sim/python.sh -m pip install --no-cache-dir boto3==1.40.0

COPY run.py /opt/isaac-sweep/run.py

ENTRYPOINT ["/isaac-sim/python.sh", "/opt/isaac-sweep/run.py"]
