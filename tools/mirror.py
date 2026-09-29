"""Spiegelt een live statische site naar de map site/ (eenmalig, bij de overstap naar Git)."""
import os, re, sys, urllib.request, urllib.parse, json
base = sys.argv[1].rstrip('/')
out = sys.argv[2] if len(sys.argv) > 2 else 'site'
host = urllib.parse.urlparse(base).netloc
seen, queue, meta = set(), ['/', '/sitemap.xml', '/robots.txt', '/404.html', '/favicon.ico', '/favicon.svg', '/site.webmanifest'], []
def add(u, cur):
    try:
        x = urllib.parse.urlparse(urllib.parse.urljoin(base + cur, u))
    except Exception:
        return
    if x.netloc not in (host, 'www.' + host, host.replace('www.', '')) or x.scheme not in ('http', 'https'):
        return
    p = urllib.parse.unquote(x.path) or '/'
    if p not in seen and p not in queue:
        queue.append(p)
while queue:
    p = queue.pop(0)
    if p in seen:
        continue
    seen.add(p)
    req = urllib.request.Request(base + urllib.parse.quote(p), headers={'User-Agent': 'Mozilla/5.0 site-mirror'})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        status = r.status
    except urllib.error.HTTPError as e:
        if p == '/404.html':
            r, status = e, 404
        else:
            meta.append([p, e.code]); continue
    except Exception as e:
        meta.append([p, str(e)]); continue
    final = urllib.parse.unquote(urllib.parse.urlparse(r.geturl()).path) or '/'
    if final != p:
        meta.append([p, '->' + final])
        if final in seen:
            continue
        seen.add(final)
    ct = r.headers.get('content-type', '')
    body = r.read()
    name = final + 'index.html' if final.endswith('/') else final
    if 'text/html' in ct and not re.search(r'\.[a-z0-9]+$', name, re.I):
        name += '.html'
    if p == '/404.html':
        name = '/404.html'
    fp = os.path.join(out, name.lstrip('/'))
    os.makedirs(os.path.dirname(fp) or '.', exist_ok=True)
    open(fp, 'wb').write(body)
    if re.search(r'html|xml|css', ct) and status == 200:
        t = body.decode('utf-8', 'replace')
        for m in re.findall(r'(?:href|src)=["\']([^"\'#]+)', t): add(m, final)
        for m in re.findall(r'content=["\'](/[^"\'#]+|https?:[^"\'#]+)', t): add(m, final)
        for s in re.findall(r'srcset=["\']([^"\']+)', t):
            for part in s.split(','): add(part.strip().split(' ')[0], final)
        for m in re.findall(r'url\(["\']?([^"\')]+)', t): add(m, final)
        for m in re.findall(r'<loc>([^<]+)', t): add(m.strip(), final)
print(json.dumps({'files': sum(len(f) for _, _, f in os.walk(out)), 'notes': meta}, indent=1))
