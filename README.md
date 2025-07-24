# PerfectPixel

PerfectPixel is a visual regression comparison tool that overlays two web pages, allowing you to visually compare layout or design differences by adjusting the overlay's transparency and syncing scrolls.

## 💡 Features

- Visual overlay of two web pages
- Scroll synchronization between pages
- Adjustable opacity slider
- CORS-bypassed proxy rendering using Flask
- Works fully offline — secure and private

---

## 🚀 Getting Started

### ✅ Requirements

- Python 3.8+
- pip
- Git (optional but recommended)
- Google Chrome or any modern browser

---

### 📦 Installation

1. Clone the repository:

```bash
git clone https://github.com/miltonakira/perfectPixel.git
cd perfectPixel
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # macOS/Linux
```

3. Install the dependencies:

```bash
pip install -r requirements.txt
```

> If you don’t have `requirements.txt`, install manually:
```bash
pip install flask requests beautifulsoup4 chardet lxml
```

---

### ▶️ Running the App

Run the application with:

```bash
python app.py
```

Or, on Windows, simply double-click the `start.bat` file if available.

The app will start on:

```
http://localhost:5000
```

---

### 🔍 How to Use

Open your browser and visit:

```
http://localhost:5000/compare?ref=https://example.com&test=https://staging.example.com
```

Replace the `ref` and `test` URLs with the pages you want to visually compare.

- The `ref` URL is the reference/original page.
- The `test` URL is the new or modified version.

You will see both pages overlaid with a slider to adjust transparency and scroll together.

---

## 📁 Project Structure

```
perfectPixel/
│
├── app.py                 # Main Flask app
├── start.bat              # Windows startup script
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **Frontend**: HTML, JavaScript, inline CSS
- **Libraries**:
  - requests
  - BeautifulSoup4
  - chardet
  - lxml
  - gzip

---

## 🙋 Author

Developed by [Milton Akira](https://github.com/miltonakira)

---

## 📄 License

This project is licensed under the MIT License.
