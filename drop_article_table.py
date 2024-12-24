from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://myuser:memo1234@localhost/ybblogdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Drop the article table
with app.app_context():
    db.engine.execute('DROP TABLE IF EXISTS article')
    print("Article table dropped.")
