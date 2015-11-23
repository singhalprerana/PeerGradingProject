sudo apt-get install python-virtualenv
mkdir PeerGrading
cd PeerGrading
virtualenv venv
. venv/bin/activate
pip install Flask
pip install flask-httpauth
