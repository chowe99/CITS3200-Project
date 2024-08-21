# CITS3200-Project

Rudimentary guide on setting up the flask server:

Create a virtual environment outside of the repository directory:


```
python3 -m venv venv
```

Activate the environment:

- WINDOWS :

  ```
  venv\Scripts\activate
  ```

- UNIX:
  ```
  source venv/bin/activate
  ```

Traverse into the flask-server directory

Install these requirements:
```
pip install flask
pip install python-dotenv
```

Run the flask app:

```
flask run
```

By default it should run on port 5000.

You can change the port number if you wish:

```
flask run -p port_number
```

Now you can just open the virtual environment and run flask if you want to use the server again.