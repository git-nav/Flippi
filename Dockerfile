FROM okteto/python:3

ENV DATABASE_URI=postgres://jvewsfdzacapgx:2fb972ab271c522fed1e874cbe153452e3a3c24bb959edd0fd62564bc5019f5e@ec2-34-193-44-192.compute-1.amazonaws.com:5432/d2bl6l1jebu7rm
ENV SECRET_KEY=ADMIN

WORKDIR /flippi

COPY . .

RUN pip install --upgrade pip && pip install -r requirements.txt

CMD ["python", "main.py"]