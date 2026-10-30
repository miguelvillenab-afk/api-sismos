FROM public.ecr.aws/lambda/python:3.12
 
# Librerías que necesita Chrome en Amazon Linux 2023
RUN dnf install -y unzip atk cups-libs gtk3 libXcomposite alsa-lib \
    libXcursor libXdamage libXext libXi libXrandr libXtst pango \
    at-spi2-atk libXt nss mesa-libgbm && dnf clean all
 
# Descargar Chrome y chromedriver (misma versión estable) en /opt
RUN VERSION=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE) && \
    curl -Lo /tmp/chrome.zip "https://storage.googleapis.com/chrome-for-testing-public/${VERSION}/linux64/chrome-linux64.zip" && \
    curl -Lo /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chrome.zip -d /opt/ && mv /opt/chrome-linux64 /opt/chrome && \
    unzip /tmp/chromedriver.zip -d /opt/ && mv /opt/chromedriver-linux64/chromedriver /opt/chromedriver && \
    rm -rf /tmp/*.zip /opt/chromedriver-linux64
 
# Dependencias de Python
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install -r ${LAMBDA_TASK_ROOT}/requirements.txt
 
# Código de la función
COPY scrap_table.py ${LAMBDA_TASK_ROOT}/
 
CMD ["scrap_table.lambda_handler"]