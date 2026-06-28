<#
Local CORS-bypass proxy (PowerShell - no installation needed)
----------------------------------------------------------------
PowerShell is already built into every Windows machine, so this script
needs no installation of Python or anything else.

What it does: takes any request (POST to change a service's status, or
GET to /v1/health/service/all to fetch real current status) coming from
the dashboard (your browser), forwards it directly to your real
provider's server (PowerShell has no browser CORS restriction), and
sends the response back to the browser with the correct CORS header
added.

How to run:
  1) Save this file (e.g. in Downloads) as proxy_server.ps1
  2) Open the Start menu, type PowerShell, click "Windows PowerShell"
     (run it from inside PowerShell - do not double-click the file)
  3) Go to the folder containing the file, e.g.:
        cd Downloads
  4) Run this command (this only bypasses policy for this one run,
     it does not change anything system-wide):
        powershell -ExecutionPolicy Bypass -File proxy_server.ps1
  5) You should see a message saying the proxy is running on
     http://127.0.0.1:2080/. Keep this window open.
  6) In the dashboard settings, set these two URLs:
        Base URL:        http://127.0.0.1:2080/v1/health/service
        Status All URL:  http://127.0.0.1:2080/v1/health/service/all

To stop, press Ctrl+C in this same window.
#>

$listenUrl    = "http://127.0.0.1:2080/"
$targetDomain = "https://your-provider.example.com"  # set this to your real provider's domain

# Header names to forward from the browser to the real server (for auth, etc.)
# Replace/extend with your own API's headers - e.g. Authorization, X-API-Key, etc.
$forwardHeaders = @("accessCode", "Cookie")

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add($listenUrl)

try {
    $listener.Start()
} catch {
    Write-Host "Failed to start proxy: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "If this mentions Access Denied, try running this script as Administrator." -ForegroundColor Yellow
    exit
}

Write-Host ("=" * 60)
Write-Host "  Local proxy running at $listenUrl"
Write-Host "  Forwarding requests to: $targetDomain"
Write-Host "  Keep this window open. Press Ctrl+C to stop."
Write-Host ("=" * 60)

while ($listener.IsListening) {
    try {
        $context  = $listener.GetContext()
        $request  = $context.Request
        $response = $context.Response

        # CORS headers on every response
        $response.Headers.Add("Access-Control-Allow-Origin", "*")
        $response.Headers.Add("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        $response.Headers.Add("Access-Control-Allow-Headers", "Content-Type, " + ($forwardHeaders -join ", "))

        if ($request.HttpMethod -eq "OPTIONS") {
            # Answer the browser's preflight request
            $response.StatusCode = 204
            $response.Close()
            continue
        }

        if ($request.HttpMethod -ne "POST" -and $request.HttpMethod -ne "GET") {
            $response.StatusCode = 405
            $response.Close()
            continue
        }

        $method = $request.HttpMethod
        $targetUrl = $targetDomain + $request.RawUrl

        $body = ""
        if ($method -eq "POST") {
            $reader = New-Object System.IO.StreamReader($request.InputStream, [System.Text.Encoding]::UTF8)
            $body = $reader.ReadToEnd()
            $reader.Close()
        }

        Write-Host ""
        Write-Host "[->] New $method request: $($request.RawUrl)"
        if ($body) { Write-Host "     Body: $body" }

        $webRequest = [System.Net.HttpWebRequest]::Create($targetUrl)
        $webRequest.Method = $method
        foreach ($h in $forwardHeaders) {
            $val = $request.Headers[$h]
            if ($val) {
                $webRequest.Headers.Add($h, $val)
                Write-Host "     $h length: $($val.Length)"
            }
        }

        $statusCode = 502
        $respBody = ""

        try {
            if ($method -eq "POST") {
                $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)
                $webRequest.ContentType = "application/json"
                $webRequest.ContentLength = $bodyBytes.Length
                $reqStream = $webRequest.GetRequestStream()
                $reqStream.Write($bodyBytes, 0, $bodyBytes.Length)
                $reqStream.Close()
            }

            $webResponse = $webRequest.GetResponse()
            $statusCode = [int]$webResponse.StatusCode

            $respStream = $webResponse.GetResponseStream()
            $respReader = New-Object System.IO.StreamReader($respStream, [System.Text.Encoding]::UTF8)
            $respBody = $respReader.ReadToEnd()
            $respReader.Close()
            $webResponse.Close()
        } catch [System.Net.WebException] {
            # The real server returned an error (e.g. 401/403) - pass it through as-is
            $errResponse = $_.Exception.Response
            if ($errResponse) {
                $statusCode = [int]$errResponse.StatusCode
                $errReader = New-Object System.IO.StreamReader($errResponse.GetResponseStream(), [System.Text.Encoding]::UTF8)
                $respBody = $errReader.ReadToEnd()
                $errReader.Close()
            } else {
                $statusCode = 502
                $respBody = "{`"proxy_error`": `"$($_.Exception.Message)`"}"
            }
        }

        Write-Host "[<-] Real server response: HTTP $statusCode"
        Write-Host "     $($respBody.Substring(0, [Math]::Min(300, $respBody.Length)))"

        $response.StatusCode = $statusCode
        $response.ContentType = "application/json"
        $respBytes = [System.Text.Encoding]::UTF8.GetBytes($respBody)
        $response.ContentLength64 = $respBytes.Length
        $response.OutputStream.Write($respBytes, 0, $respBytes.Length)
        $response.Close()

    } catch {
        Write-Host "[x] Internal proxy error: $($_.Exception.Message)" -ForegroundColor Red
        try { $response.Close() } catch {}
    }
}
