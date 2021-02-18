### Test task 
Not difficult test task with tricky terms/and conditions.
Just one model few functions and tests to cover them.

The problem in such way of resolving - 
bulk-operations (including update operations) works without save signlas, and simple task
becomes lage code canvas.
I can't figure out the way without overriding save(), maybe i should have play around 
with postgres constraints...


to run:
save project to your local
from the root project directory:
```sh
pip install -r requirements.txt
```
create local db
```sh
python3 manage.py migrate
```
to run dev sever :
```sh
python3 manage.py runserver
```
to run test suit:
```sh
pytest
```

[source task](https://drive.google.com/file/d/1YFuH-924__j5RbJ6v3lahixcxU21jnbh/) 