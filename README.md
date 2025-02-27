# vowerp3be

This is the backend for a webapp which will be a multitenant app for an erp solution, using nextjs for frontend and python for backend.

VOW ERP3 Backend python


docker build command 
docker build -t vowerp3be-docker .

run command 
docker run -d -p 8000:8000 --env-file .env --name vowerp3be vowerp3be-docker

stop container command
docker stop vowerp3be

remove container command
docker rm vowerp3be-docker


 run tests inside the container, you can override the default Docker CMD:
docker build -t vowerp3be-docker .
docker run --rm -it vowerp3be-docker pytest
Alternatively, you can use a command in your Dockerfile or Docker Compose to handle tests, but the simplest approach is to run a container that executes pytest.


