FROM okteto/python:3

ENV DATABASE_URI=postgres://juqtbhqw:WOY-JwUVYDawfpcVFlG__wUawXnOkvxg@jelani.db.elephantsql.com/juqtbhqw
ENV SECRET_KEY=ADMIN

WORKDIR /flippi

COPY . .

RUN pip install --upgrade pip && pip install -r requirements.txt

CMD ["python", "main.py"]