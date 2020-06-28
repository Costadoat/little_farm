source /django/jardin/mvpappenv/bin/activate
gunicorn --workers 3 --bind unix:jardin_display.sock -m 007 wsgi
deactivate