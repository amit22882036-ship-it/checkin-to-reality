# Flask Application

A basic Flask web application structure.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

```bash
python app.py
```

The application will be available at `http://127.0.0.1:5000/`

## Project Structure

```
.
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates
│   ├── base.html      # Base template
│   ├── index.html     # Home page
│   └── about.html     # About page
└── static/            # Static files
    └── css/
        └── style.css  # Stylesheet
```
