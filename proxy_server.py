# -*- coding: utf-8 -*-
"""
پروکسی محلی برای دور زدن محدودیت CORS
---------------------------------------
این اسکریپت فقط روی کامپیوتر خودت اجرا می‌شه و هیچ سروری بیرون از کامپیوترت
بهش دسترسی ندارد (فقط روی 127.0.0.1 گوش می‌ده).

کارش: هر درخواستی (POST برای تغییر وضعیت، GET برای گرفتن وضعیت واقعی همه‌ی
سرویس‌ها) رو از داشبورد (مرورگر) می‌گیره، خودش مستقیماً به همون مسیر روی
سرور واقعی دامنه‌ی واقعی می‌فرسته (چون پایتون محدودیت CORS مرورگر رو ندارد)،
و جواب واقعی سرور رو با هدر CORS درست برمی‌گردونه به مرورگر.

این پروکسی به مسیر (path) درخواست توجه می‌کنه، یعنی هم از این آدرس‌ها
پشتیبانی می‌کنه:
    http://127.0.0.1:2080/v1/health/service       (POST - تغییر وضعیت)
    http://127.0.0.1:2080/v1/health/service/all   (GET  - گرفتن وضعیت واقعی)

اجرا:
    python proxy_server.py

بعد از اجرا، توی تنظیمات داشبورد (دکمه ⚙ تنظیمات اتصال)، مقادیر Base URL و
Status-All URL رو به این آدرس‌ها تغییر بده:
    Base URL:        http://127.0.0.1:2080/v1/health/service
    Status All URL:  http://127.0.0.1:2080/v1/health/service/all

این پنجره (ترمینال) باید باز بمونه تا وقتی داشبورد رو استفاده می‌کنی.
برای توقف، Ctrl+C رو بزن.
"""

import json
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

# دامنه‌ی واقعی سرور بانک (مسیر از روی درخواست مرورگر تعیین می‌شه)
# این مقدار رو با دامنه‌ی واقعی سرویس‌دهنده‌ی شما جایگزین کن
TARGET_DOMAIN = "https://your-provider.example.com"

# پورت محلی که پروکسی روش گوش می‌ده
LISTEN_PORT = 2080

# اسم هدرهایی که باید از مرورگر به سرور واقعی منتقل شن (برای auth و غیره).
# با هدرهای API خودتون جایگزین/تکمیلش کنید — مثلاً Authorization, X-API-Key, و غیره.
FORWARD_HEADERS = ["accessCode", "Cookie"]


class ProxyHandler(BaseHTTPRequestHandler):

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, " + ", ".join(FORWARD_HEADERS))
        self.send_header("Access-Control-Max-Age", "86400")

    # درخواست preflight که مرورگر قبل از درخواست واقعی می‌فرسته
    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        self._forward(method="GET")

    def do_POST(self):
        self._forward(method="POST")

    def _forward(self, method):
        try:
            target_url = TARGET_DOMAIN + self.path

            body = None
            if method == "POST":
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length) if content_length > 0 else b"{}"

            headers = {}
            for h in FORWARD_HEADERS:
                val = self.headers.get(h, "")
                if val:
                    headers[h] = val

            print(f"\n[→] درخواست {method} جدید: {self.path}")
            if body is not None:
                print(f"    بدنه: {body.decode('utf-8', errors='replace')}")
            for h in FORWARD_HEADERS:
                if h in headers:
                    print(f"    {h} طول: {len(headers[h])}")

            if body is not None:
                headers["Content-Type"] = "application/json"

            req = urllib.request.Request(
                target_url,
                data=body,
                method=method,
                headers=headers,
            )

            try:
                with urllib.request.urlopen(req, timeout=15) as upstream_res:
                    status = upstream_res.status
                    resp_body = upstream_res.read()
            except urllib.error.HTTPError as http_err:
                # سرور واقعی یه خطا برگردونده (مثلاً 401، 403، 400) — این رو عیناً به مرورگر منتقل می‌کنیم
                status = http_err.code
                resp_body = http_err.read()
            except urllib.error.URLError as url_err:
                print(f"[✗] خطا در اتصال به سرور واقعی: {url_err}")
                self.send_response(502)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"proxy_error": f"اتصال به سرور برقرار نشد: {str(url_err)}"}).encode("utf-8")
                )
                return

            print(f"[←] پاسخ سرور واقعی: HTTP {status}")
            print(f"    {resp_body.decode('utf-8', errors='replace')[:300]}")

            self.send_response(status)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp_body)

        except Exception as e:
            print(f"[✗] خطای داخلی پروکسی: {e}")
            self.send_response(500)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"proxy_error": str(e)}).encode("utf-8"))

    # لاگ‌های پیش‌فرض http.server رو ساده‌تر می‌کنیم
    def log_message(self, format, *args):
        pass


def main():
    server = HTTPServer(("127.0.0.1", LISTEN_PORT), ProxyHandler)
    print("=" * 60)
    print(f"  پروکسی محلی روی http://127.0.0.1:{LISTEN_PORT} اجرا شد")
    print(f"  درخواست‌ها به این دامنه فوروارد می‌شن: {TARGET_DOMAIN}")
    print("  این پنجره رو باز نگه دار. برای توقف Ctrl+C بزن.")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nپروکسی متوقف شد.")
        server.shutdown()


if __name__ == "__main__":
    main()
