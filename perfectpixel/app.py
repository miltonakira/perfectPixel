from flask import Flask, request, render_template_string, Response
from urllib.parse import urljoin, urlparse, quote
from playwright.async_api import async_playwright  
from collections import defaultdict
import os
import requests
import re
import time
import sys
import atexit
import asyncio

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"

app = Flask(__name__)

playwright_instance = None
browser = None
page = None

def get_headless_shell_path():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    
    return os.path.join(
        base_path,
        "_internal",
        "playwright_browsers",
        "chromium_headless_shell-1169",
        "chrome-win",
        "headless_shell.exe"
    )
    
def init_browser():
    global playwright_instance, browser, page
    if browser is None:
        asyncio.run(_start_browser())

async def _start_browser():
    global playwright_instance, browser, page
    from playwright.async_api import async_playwright
    playwright_instance = await async_playwright().start()
    browser = await playwright_instance.chromium.launch(
        headless=True,
        executable_path=get_headless_shell_path()
    )
    page = await browser.new_page()
    await page.goto("http://localhost:5000")

@atexit.register
def shutdown_browser():
    if page:
        page.close()
    if browser:
        browser.close()
    if playwright_instance:
        playwright_instance.stop()
        
@app.route("/proxy-script")
def proxy_script():
    script_url = request.args.get("url")
    if not script_url:
        return "Missing script URL", 400
    try:
        resp = requests.get(script_url)
        headers = {
            "Content-Type": resp.headers.get("Content-Type", "application/javascript"),
            "Access-Control-Allow-Origin": "*",
        }
        return Response(resp.content, status=resp.status_code, headers=headers)
    except Exception as e:
        return f"Proxy Script Error: {e}", 500

@app.route("/proxy-font")
def proxy_font():
    font_url = request.args.get("url")
    if not font_url:
        return "Missing URL", 400
    try:
        resp = requests.get(font_url, stream=True)
        headers = {
            "Content-Type": resp.headers.get("Content-Type", "application/octet-stream"),
            "Access-Control-Allow-Origin": "*",
        }
        return Response(resp.content, status=resp.status_code, headers=headers)
    except Exception as e:
        return f"Proxy Font Error: {e}", 500

def inject_scroll_override(html):
    style_tag = """
    <style>
    html, body, * {
        scroll-behavior: auto !important;
    }
    </style>
    """
    if "<head>" in html:
        return html.replace("<head>", f"<head>{style_tag}")
    else:
        return style_tag + html
    
def rewrite_relative_paths(html: str, base_url: str) -> str:
    def replace_attr(attr):
        pattern = fr'{attr}=(["\'])(?!#)([^"\']+)\1'
        return re.sub(pattern, lambda m: f'{attr}="{urljoin(base_url, m.group(2))}"', html)

    for attr in ['src', 'href', 'action', 'data-src']:
        html = replace_attr(attr)

    html = re.sub(
        r'url\((?!data:|#)(["\']?)([^"\')]+)\1\)',
        lambda m: f'url("/proxy-font?url={quote(urljoin(base_url, m.group(2)))}")',
        html
    )

    html = re.sub(
        r'<script\s+[^>]*src=["\']([^"\']+)["\']',
        # lambda m: f'<script src="/proxy-script?url={quote(urljoin(base_url, m.group(1)))}"',
        lambda m: f'<script src="{urljoin(base_url, m.group(1))}"',
        html
    )
    
    html = re.sub(r'<iframe[^>]*aria-hidden=["\']true["\'][^>]*>.*?</iframe>', '', html, flags=re.DOTALL | re.IGNORECASE)


    return html
    
@app.route("/proxy")
def proxy():
    url = request.args.get("url")
    if not url:
        return "Missing URL", 400

    try:
        html = asyncio.run(render_page(url))
        return Response(html, content_type="text/html")
    except Exception as e:
        return f"Erro Playwright: {e}", 500

async def render_page(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path=get_headless_shell_path(),
            args=["--no-sandbox", "--disable-gpu"]
        )
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        content = await page.content()
        await browser.close()

    # Processa HTML
    fixed_content = rewrite_relative_paths(content, url)
    fixed_content = inject_scroll_override(fixed_content)

    injected_script = """
<script>
(function simulateActivity() {
  const events = [
    new MouseEvent("mousemove", { bubbles: true }),
    new Event("scroll", { bubbles: true }),
    new Event("resize"),
    new MouseEvent("click", { bubbles: true }),
  ];
  events.forEach(e => window.dispatchEvent(e));
  setTimeout(() => {
    events.forEach(e => window.dispatchEvent(e));
  }, 500);
})();
window.addEventListener('load', () => {
  setTimeout(() => {
    window.parent.postMessage("full-loaded", "*");
  }, 300);
});
</script>
"""

    if "</body>" in fixed_content:
        fixed_content = fixed_content.replace("</body>", injected_script + "\n</body>")
    else:
        fixed_content += injected_script

    return fixed_content

@app.route('/compare2')
def compare2():
    ref_url = request.args.get('ref')
    test_url = request.args.get('test')

    if not ref_url or not test_url:
        return 'Parâmetros ?ref= e ?test= são obrigatórios.', 400

    timestamp = int(time.time())

    def get_src(url):
        parsed = urlparse(url)
        is_local = parsed.hostname in ['localhost', '127.0.0.1']
        return url if is_local else f"/proxy?url={url}&t={timestamp}"

    base_src = get_src(test_url)
    overlay_src = get_src(ref_url)

    html = f'''
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
        }}
        iframe {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            border: none;
            pointer-events: auto;
        }}
        #overlay {{
            z-index: 2;
            opacity: 0.5;
        }}
        #base {{
            z-index: 1;
            opacity: 1;
        }}
        #controlBtn {{
            position: fixed;
            top: 10px;
            left: 10px;
            z-index: 9999;
            padding: 8px 12px;
            background: #007bff;
            color: white;
            font-family: sans-serif;
            font-size: 14px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }}
        #controlModal {{
            position: fixed;
            top: 60px;
            left: 10px;
            z-index: 10000;
            background: white;
            border: 1px solid #ccc;
            padding: 12px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            font-family: sans-serif;
            display: none;
            width: 280px;
        }}
        #controlModal h3 {{
            margin-top: 0;
            font-size: 16px;
            color: #333;
        }}
        .control-group {{
            margin-bottom: 12px;
        }}
        .control-group label {{
            font-size: 13px;
            display: block;
            margin-bottom: 4px;
        }}
        .control-group input[type="range"],
        .control-group input[type="number"] {{
            width: 100%;
        }}
        .close-btn {{
            float: right;
            cursor: pointer;
            color: #999;
            font-weight: bold;
        }}
        .checkbox-group {{
            margin-top: 10px;
            font-size: 13px;
        }}
    </style>

    <iframe src="{base_src}" id="base"></iframe>
    <iframe src="{overlay_src}" id="overlay"></iframe>

    <button id="controlBtn">⚙️ Controles</button>

    <div id="controlModal">
        <div>
            <span class="close-btn" onclick="document.getElementById('controlModal').style.display='none'">×</span>
            <h3>Controles</h3>
        </div>

        <div class="control-group">
            <label>Scroll Base:</label>
            <input type="range" id="baseScroll" min="0" max="10000" step="10">
            <input type="number" id="baseScrollNum" min="0" max="10000">
        </div>

        <div class="control-group">
            <label>Scroll Overlay:</label>
            <input type="range" id="overlayScroll" min="0" max="10000" step="10">
            <input type="number" id="overlayScrollNum" min="0" max="10000">
        </div>

        <div class="control-group">
            <label>Transparência Base:</label>
            <input type="range" id="baseOpacity" min="0" max="100" value="100">
        </div>

        <div class="control-group">
            <label>Transparência Overlay:</label>
            <input type="range" id="overlayOpacity" min="0" max="100" value="50">
        </div>

        <div class="checkbox-group">
            <label>
                <input type="checkbox" id="forceScroll">
                Forçar sincronização de scroll
            </label>
        </div>
    </div>

    <script>
        const baseFrame = document.getElementById('base');
        const overlayFrame = document.getElementById('overlay');

        const controlBtn = document.getElementById('controlBtn');
        const modal = document.getElementById('controlModal');

        controlBtn.addEventListener('click', () => {{
            modal.style.display = modal.style.display === 'block' ? 'none' : 'block';
        }});

        // Scroll Base
        const baseScroll = document.getElementById('baseScroll');
        const baseScrollNum = document.getElementById('baseScrollNum');

        baseScroll.addEventListener('input', () => {{
            baseScrollNum.value = baseScroll.value;
            baseFrame.contentWindow.scrollTo(0, baseScroll.value);
            if (document.getElementById('forceScroll').checked) {{
                overlayFrame.contentWindow.scrollTo(0, baseScroll.value);
            }}
        }});
        baseScrollNum.addEventListener('input', () => {{
            baseScroll.value = baseScrollNum.value;
            baseFrame.contentWindow.scrollTo(0, baseScrollNum.value);
            if (document.getElementById('forceScroll').checked) {{
                overlayFrame.contentWindow.scrollTo(0, baseScrollNum.value);
            }}
        }});

        // Scroll Overlay
        const overlayScroll = document.getElementById('overlayScroll');
        const overlayScrollNum = document.getElementById('overlayScrollNum');

        overlayScroll.addEventListener('input', () => {{
            overlayScrollNum.value = overlayScroll.value;
            overlayFrame.contentWindow.scrollTo(0, overlayScroll.value);
            if (document.getElementById('forceScroll').checked) {{
                baseFrame.contentWindow.scrollTo(0, overlayScroll.value);
            }}
        }});
        overlayScrollNum.addEventListener('input', () => {{
            overlayScroll.value = overlayScrollNum.value;
            overlayFrame.contentWindow.scrollTo(0, overlayScrollNum.value);
            if (document.getElementById('forceScroll').checked) {{
                baseFrame.contentWindow.scrollTo(0, overlayScrollNum.value);
            }}
        }});

        // Opacidade
        const overlayOpacity = document.getElementById('overlayOpacity');
        const baseOpacity = document.getElementById('baseOpacity');

        overlayOpacity.addEventListener('input', () => {{
            overlayFrame.style.opacity = overlayOpacity.value / 100;
        }});
        baseOpacity.addEventListener('input', () => {{
            baseFrame.style.opacity = baseOpacity.value / 100;
        }});
    </script>
    '''

    return render_template_string(html)

    
@app.route('/compare')
def compare():
    ref_url = request.args.get('ref')
    test_url = request.args.get('test')

    if not ref_url or not test_url:
        return 'Parâmetros ?ref= e ?test= are required.', 400
    
    proxy_usage_total = 0
    
    def get_src(url):
        nonlocal proxy_usage_total
        timestamp = int(time.time())
        parsed = urlparse(url)
        is_local = parsed.hostname in ['localhost', '127.0.0.1']
        if not is_local:
            proxy_usage_total += 1
            return f"/proxy?url={url}&t={timestamp}"
        return url

    base_src = get_src(test_url)
    overlay_src = get_src(ref_url)

    html = f'''
    
    <meta name="viewport" content="width=375, initial-scale=1">
    <style>
        #loader {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: white;
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
            color:#666;
            font-family:verdana;
            font-size:16px;
        }}
        .loader-svg {{
            width: 64px;
            height: 64px;
        }}
        .loader-circle {{
            fill: none;
            stroke: #4a90e2;
            stroke-width: 6;
            stroke-linecap: round;
            stroke-dasharray: 150;
            stroke-dashoffset: 0;
            animation: dash 1.5s ease-in-out infinite, rotate 2s linear infinite;
            transform-origin: center;
        }}
        @keyframes rotate {{
            100% {{ transform: rotate(360deg); }}
        }}
        @keyframes dash {{
            0% {{
                stroke-dasharray: 1, 150;
                stroke-dashoffset: 0;
            }}
            50% {{
                stroke-dasharray: 90, 150;
                stroke-dashoffset: -35;
            }}
            100% {{
                stroke-dasharray: 90, 150;
                stroke-dashoffset: -124;
            }}
        }}
        
        html, body {{
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
        }}
        iframe {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            border: none;
        }}
        #overlay {{
            pointer-events:none;
            opacity: 0.5;
            z-index: 2;
            
        }}
        #base {{
            z-index: 1;
        }}
        
        #slider {{
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 9999;
            background: rgba(255,255,255,0.8);
            padding: 5px 10px;
            border-radius: 8px;
            font-family: sans-serif;
        }}
    </style>
    
    <div id="loader">
        <svg class="loader-svg" viewBox="0 0 50 50">
            <circle class="loader-circle" cx="25" cy="25" r="20" />
        </svg>
        <br/>
        <div style="display:block;">
            Patience is a virtue
        </div>
    </div>
    
    <iframe src="{base_src}" id="base"></iframe>
    <iframe src="{overlay_src}" id="overlay"></iframe>


    <div id="slider">
        <input type="range" id="opacityRange" min="0" max="100" value="50">
    </div>

    <script>
    const base = document.getElementById('base');
    const overlay = document.getElementById('overlay');
    const opacityRange = document.getElementById('opacityRange');
    const loader = document.getElementById('loader');
    let loaded = 0;
    
    let loadedCount = 0;

    opacityRange.addEventListener('input', (e) => {{
        overlay.style.opacity = e.target.value / 100;
    }});
    
    window.addEventListener("message", (event) => {{
        if (event.data === "full-loaded") {{
            loaded++;
            if({proxy_usage_total} <= loaded) {{
                if (loader) loader.style.display = 'none';
            }}
        }}
    }});
    
    window.addEventListener('DOMContentLoaded', () => {{
        const base = document.getElementById('base');
        const overlay = document.getElementById('overlay');

        function syncScrollPrecisely(sourceWin, targetWin) {{
            let ticking = false;

            sourceWin.addEventListener('scroll', () => {{
                if (!ticking) {{
                    window.requestAnimationFrame(() => {{
                        try {{
                            const top = sourceWin.scrollY;
                            const left = sourceWin.scrollX;
                            targetWin.scrollTo({{ top, left, behavior: 'auto' }});
                        }} catch (e) {{
                            console.error('Erro ao sincronizar scroll:', e);
                        }}
                        ticking = false;
                    }});
                    ticking = true;
                }}
            }});
        }}

        base.addEventListener('load', () => {{
            const baseWin = base.contentWindow;
            const overlayWin = overlay?.contentWindow;

            if (baseWin && overlayWin) {{
                syncScrollPrecisely(baseWin, overlayWin);
            }}
        }}, {{ once: true }});
        
    }});

  
    </script>
    '''
    return render_template_string(html)

@app.route('/')
def index():
    html = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=375, initial-scale=1" />
  <title>Perfect Pixel</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Inter', sans-serif;
      background-color: #121212;
      color: #f1f1f1;
      height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 20px;
    }

    .container {
      background-color: #1e1e1e;
      padding: 40px;
      border-radius: 12px;
      max-width: 480px;
      width: 100%;
      box-shadow: 0 0 20px rgba(0,0,0,0.4);
    }

    h2 {
      text-align: center;
      margin-bottom: 24px;
      color: #ffffff;
      font-size: 24px;
      font-weight: 600;
    }

    label {
      display: block;
      margin-bottom: 8px;
      font-weight: 500;
      color: #ccc;
    }

    input[type="text"] {
      width: 100%;
      padding: 12px;
      margin-bottom: 20px;
      border: 1px solid #333;
      border-radius: 6px;
      background-color: #2a2a2a;
      color: #f1f1f1;
      font-size: 14px;
    }

    input[type="text"]::placeholder {
      color: #777;
    }

    input[type="submit"] {
      width: 100%;
      padding: 14px;
      background-color: #00c896;
      border: none;
      color: white;
      font-size: 16px;
      font-weight: 600;
      border-radius: 6px;
      cursor: pointer;
      transition: background-color 0.3s ease;
    }

    input[type="submit"]:hover {
      background-color: #00a97d;
    }

    @media (max-width: 600px) {
      .container {
        padding: 30px 20px;
      }
    }
  </style>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
</head>
<body>
  <div class="container">
    <h2>Perfect Pixel</h2>
    <form action="/compare" method="get">
      <label for="ref">Reference URL</label>
      <input type="text" id="ref" name="ref" placeholder="https://site.com" required />

      <label for="test">Your URL</label>
      <input type="text" id="test" name="test" placeholder="http://localhost:4321" required />

      <input type="submit" value="Compare">
    </form>
  </div>
</body>
</html>

    '''
    return render_template_string(html)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)