import urllib.request
try:
    r = urllib.request.urlopen("https://mirrors.aliyun.com/pypi/simple/", timeout=5)
    print("OK", r.status)
except Exception as e:
    print("FAIL", type(e).__name__, e)
