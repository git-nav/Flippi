FROM okteto/python:3

WORKDIR /flippi

COPY . .

RUN pip install --upgrade pip && pip install -r requirements.txt

CMD ["python", "main.py"]