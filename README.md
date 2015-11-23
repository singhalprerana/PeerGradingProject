## Peer Grading and Review System

Peer Grading and Review System is a grading and feedback system for courses with peer grading structure. 
It is built as a part of Software Engineering course project. It is a built using **Python Flask Microframework**, **SQLite** database, **Materialize CSS**.

## Installation

1. Install python-flask in a virtual environment. [Flask Installation using Virtual Environment](http://flask.pocoo.org/docs/0.10/installation/)
2. Install flask-httpauth. [Flask HTTPAuth docs](https://flask-httpauth.readthedocs.org/en/latest/)
>  pip install flask-httpauth 
3. Go to the web directory where the code is installed on the server in command prompt/terminal. 
4. Find the python file db.py and execute it.
5. Hit the URL at which you have setup the project 
>  http://localhost:5000/
6. You should get the home page of the application.

## Quick Start

If you are on Linux, you can ignore steps 1, 2 and 3 and simply run setup.sh to install the project instead.

## API Usage
1. Download user information (Authentication privilege : Admin) :: http://localhost:5000/api/download_userinfo/
2. Add users (Authentication privilege : Admin) :: http://localhost:5000/api/add_users/
3. Download Grades (Authentication privilege : Instructor) :: http://localhost:5000/api/download_grades/
4. Add grades (Authentication privilege : Instructor) :: http://localhost:5000/api/add_grades/


## Developers

* Vaibhav Tripathi
* Prerana Singhal

## Official Documentation

Documentation for the framework can be found on the [Flask documentation](http://flask.pocoo.org/docs/0.10/).

### License

This project is open-sourced software.
