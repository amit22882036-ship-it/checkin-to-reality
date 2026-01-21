from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'


@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')


if __name__ == '__main__':
    app.run(debug=True)
