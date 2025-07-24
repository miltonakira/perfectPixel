from flask import Flask, request, render_template_string, Response, make_response
import requests
from bs4 import BeautifulSoup
import gzip
from io import BytesIO
import chardet
from urllib.parse import urljoin, urlparse
import re
import time



def run():
    app = Flask(__name__)

    @app.route("/proxy")
    def proxy():
        url = request.args.get("url")
        if not url:
            return "Missing URL", 400
        try:
            print(f"[Proxy] Fetching: {url}")
            resp = requests.get(url, stream=True)
            content = resp.raw.read()
            return Response(content, content_type=resp.headers.get("Content-Type"))

        except Exception as e:
            return f"Proxy Error: {e}", 500
        
    @app.route('/clone')
    def clone():
        url = request.args.get('url')
        if not url:
            return 'Missing URL', 400

        headers = {k: v for k, v in request.headers if k.lower() != 'host'}
        headers['Accept-Encoding'] = 'gzip'

        try:
            resp = requests.get(url, headers=headers)
            raw = resp.raw.read()

            if resp.headers.get('Content-Encoding') == 'gzip' or raw[:2] == b'\x1f\x8b':
                content = gzip.decompress(raw)
            else:
                content = raw

            content = resp.content
            encoding = resp.encoding or chardet.detect(content)['encoding'] or 'utf-8'
            decoded = content.decode(encoding, errors='replace')
            
            content_type = resp.headers.get('Content-Type', '').lower()

            if 'text/html' in content_type or b'<html' in content[:500].lower():    
                soup = BeautifulSoup(decoded, 'html.parser')
                base_url = url
                tags_attrs = {
                    'img': 'src',
                    'script': 'src',
                    'link': 'href',
                    'source': 'src',
                    'video': 'src',
                    'audio': 'src',
                    'iframe': 'src',
                }

                for tag, attr in tags_attrs.items():
                    for el in soup.find_all(tag):
                        src = el.get(attr)
                        if src and not src.startswith(('http://', 'https://', '//', 'data:')):
                            full_url = urljoin(base_url, src)
                            el[attr] = full_url

                # Ajusta fontes e urls no <style> precisa do bendito proxy
                for style in soup.find_all("style"):
                    if style.string:
                        cleaned_css = re.sub(r'local\([^)]+\),\s*', '', style.string)
                        updated_css = re.sub(
                            r'url\((["\']?)(\/[^)\'"]+)\1\)',
                            lambda m: f"url('/proxy?url={urljoin(base_url, m.group(2))}')",
                            cleaned_css
                        )
                        style.string.replace_with(updated_css)

                html = soup.prettify()
                # return Response(soup.prettify(), content_type='text/html; charset=utf-8')
                response = make_response(soup.prettify())
                response.headers['Content-Type'] = 'text/html'
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response

            return Response(content, content_type=resp.headers.get('Content-Type'))

        except Exception as e:
            print(">>> Proxy Error:", e)
            return f"Erro ao processar a URL: {e}", 500
        
    @app.route('/compare')
    def compare():
        ref_url = request.args.get('ref')
        test_url = request.args.get('test')

        if not ref_url or not test_url:
            return 'Parâmetros ?ref= e ?test= são obrigatórios.', 400
        
        timestamp = int(time.time())


        html = f'''
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
                pointer-events: none;
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
        
        <iframe src="/clone?url={test_url}&t={timestamp}" id="base"></iframe>
        <iframe src="/clone?url={ref_url}&t={timestamp}" id="overlay"></iframe>

        <div id="slider">
            <input type="range" id="opacityRange" min="0" max="100" value="50">
        </div>

        <script>
        const base = document.getElementById('base');
        const overlay = document.getElementById('overlay');
        const opacityRange = document.getElementById('opacityRange');
        let loadedCount = 0;

        opacityRange.addEventListener('input', (e) => {{
            overlay.style.opacity = e.target.value / 100;
        }});
        
        window.addEventListener('DOMContentLoaded', () => {{
            const base = document.getElementById('base');
            const overlay = document.getElementById('overlay');
            
            if(base && overlay) {{
                base.addEventListener('load', () => {{
                    const baseWin = base.contentWindow;
                    
                    if(loader) loader.style.display = 'none';

                    baseWin.addEventListener('scroll', () => {{
                        try {{
                            const top = baseWin.scrollY;
                            const left = baseWin.scrollX;
                            overlay.contentWindow.scrollTo(left, top);
                        }} catch (e) {{
                            console.error('Erro ao sincronizar scroll:', e);
                        }}
                    }});
                }});
            }}
            
            window.addEventListener('load', () => {{
                const loader = document.getElementById('loader');
                if (loader) {{
                    loader.style.display = 'none';
                }}
            }});
            
        }});
        </script>
        '''
        return render_template_string(html)

    @app.route('/')
    def index():
        html = '''
        <h2>Perfect Pixel</h2>
        <form action="/compare" method="get">
            <label>Reference (ex: https://site.com):</label><br>
            <input type="text" name="ref" style="width: 500px;"><br><br>
            <label>Your URL (ex: http://localhost:4321):</label><br>
            <input type="text" name="test" style="width: 500px;"><br><br>
            <input type="submit" value="Comparar">
        </form>
        '''
        return render_template_string(html)

    app.run(debug=True, port=5000)