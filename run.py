
from app import create_app, db
# from flask import Flask, render_template
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
