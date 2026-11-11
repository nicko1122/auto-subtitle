param(
    [Parameter(Mandatory=$true)][string]$BrowserExe,
    [Parameter(Mandatory=$true)][string]$HtmlPath,
    [Parameter(Mandatory=$true)][string]$ManifestJsonPath,
    [Parameter(Mandatory=$true)][string]$OutDir,
    [int]$Width = 1920,
    [int]$Height = 1080
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$UserDataDir = Join-Path $OutDir ("chrome_profile_" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $UserDataDir | Out-Null

$code = @"
using System;
using System.IO;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Web.Script.Serialization;

public class AutoSubCdpRenderer {
    private static JavaScriptSerializer _json = new JavaScriptSerializer() { MaxJsonLength = 67108864 };
    private static int _nextId = 1;

    private static async Task<string> RecvFullAsync(ClientWebSocket ws) {
        var ms = new MemoryStream();
        var buf = new byte[65536];
        while (true) {
            var res = await ws.ReceiveAsync(new ArraySegment<byte>(buf), CancellationToken.None);
            ms.Write(buf, 0, res.Count);
            if (res.EndOfMessage) break;
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }

    private static async Task<Dictionary<string, object>> CallAsync(ClientWebSocket ws, string method, Dictionary<string, object> p) {
        int id = _nextId++;
        var req = new Dictionary<string, object> { { "id", id }, { "method", method } };
        if (p != null) req["params"] = p;
        var bytes = Encoding.UTF8.GetBytes(_json.Serialize(req));
        await ws.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, CancellationToken.None);

        while (true) {
            var msg = await RecvFullAsync(ws);
            var obj = _json.Deserialize<Dictionary<string, object>>(msg);
            if (obj.ContainsKey("id") && Convert.ToInt32(obj["id"]) == id) {
                if (obj.ContainsKey("error")) {
                    throw new Exception("CDP error on " + method + ": " + _json.Serialize(obj["error"]));
                }
                return obj.ContainsKey("result") ? (Dictionary<string, object>)obj["result"] : new Dictionary<string, object>();
            }
        }
    }

    public static string Run(string wsUrl, string htmlUrl, string manifestJson, string outDir, int width, int height) {
        return RunAsync(wsUrl, htmlUrl, manifestJson, outDir, width, height).GetAwaiter().GetResult();
    }

    private static async Task<string> RunAsync(string wsUrl, string htmlUrl, string manifestJson, string outDir, int width, int height) {
        var swTotal = System.Diagnostics.Stopwatch.StartNew();
        using (var ws = new ClientWebSocket()) {
            await ws.ConnectAsync(new Uri(wsUrl), CancellationToken.None);

            await CallAsync(ws, "Page.enable", null);
            await CallAsync(ws, "Runtime.enable", null);
            await CallAsync(ws, "Emulation.setDeviceMetricsOverride", new Dictionary<string, object> {
                { "width", width },
                { "height", height },
                { "deviceScaleFactor", 1 },
                { "mobile", false }
            });
            await CallAsync(ws, "Emulation.setDefaultBackgroundColorOverride", new Dictionary<string, object> {
                { "color", new Dictionary<string, object> { { "r", 0 }, { "g", 0 }, { "b", 0 }, { "a", 0 } } }
            });

            await CallAsync(ws, "Page.navigate", new Dictionary<string, object> { { "url", htmlUrl } });
            await CallAsync(ws, "Runtime.evaluate", new Dictionary<string, object> {
                { "expression", "new Promise(r => { if (document.readyState === 'complete') document.fonts.ready.then(() => requestAnimationFrame(() => r('ok'))); else window.addEventListener('load', () => document.fonts.ready.then(() => requestAnimationFrame(() => r('ok')))); })" },
                { "awaitPromise", true }
            });

            var items = _json.Deserialize<List<Dictionary<string, object>>>(manifestJson);

            await CallAsync(ws, "Runtime.evaluate", new Dictionary<string, object> {
                { "expression", "window.setSubText('')" },
                { "awaitPromise", true }
            });
            var blankShot = await CallAsync(ws, "Page.captureScreenshot", new Dictionary<string, object> {
                { "format", "png" },
                { "fromSurface", true }
            });
            File.WriteAllBytes(Path.Combine(outDir, "blank.png"), Convert.FromBase64String((string)blankShot["data"]));

            foreach (var item in items) {
                string fileName = (string)item["file"];
                string text = (string)item["text"];
                string jsExpr = "window.setSubText(" + _json.Serialize(text) + ")";
                await CallAsync(ws, "Runtime.evaluate", new Dictionary<string, object> {
                    { "expression", jsExpr },
                    { "awaitPromise", true }
                });
                var shot = await CallAsync(ws, "Page.captureScreenshot", new Dictionary<string, object> {
                    { "format", "png" },
                    { "fromSurface", true }
                });
                File.WriteAllBytes(Path.Combine(outDir, fileName), Convert.FromBase64String((string)shot["data"]));
            }
            swTotal.Stop();

            var summary = new Dictionary<string, object> {
                { "count", items.Count },
                { "elapsed_ms", swTotal.ElapsedMilliseconds }
            };
            return _json.Serialize(summary);
        }
    }
}
"@

Add-Type -TypeDefinition $code -ReferencedAssemblies "System.Web.Extensions"

$proc = Start-Process $BrowserExe -ArgumentList `
    "--headless=new", `
    "--disable-gpu", `
    "--no-first-run", `
    "--no-default-browser-check", `
    "--remote-allow-origins=*", `
    "--allow-file-access-from-files", `
    "--user-data-dir=$UserDataDir", `
    "--remote-debugging-port=0", `
    "about:blank" -PassThru

try {
    $portFile = Join-Path $UserDataDir "DevToolsActivePort"
    $port = $null
    for ($i = 0; $i -lt 80; $i++) {
        if (Test-Path $portFile) {
            $lines = Get-Content $portFile -ErrorAction SilentlyContinue
            if ($lines -and $lines.Count -ge 1 -and $lines[0].Trim() -match "^\d+$") {
                $port = $lines[0].Trim()
                break
            }
        }
        Start-Sleep -Milliseconds 50
    }
    if (-not $port) {
        throw "Headless browser DevToolsActivePort timed out"
    }

    $wsUrl = $null
    for ($i = 0; $i -lt 50; $i++) {
        try {
            $targets = Invoke-RestMethod "http://127.0.0.1:$port/json/list" -TimeoutSec 2
            $page = $targets | Where-Object { $_.type -eq "page" } | Select-Object -First 1
            if ($page -and $page.webSocketDebuggerUrl) {
                $wsUrl = $page.webSocketDebuggerUrl
                break
            }
        } catch {
            Start-Sleep -Milliseconds 50
        }
        Start-Sleep -Milliseconds 50
    }
    if (-not $wsUrl) {
        throw "Headless browser page target did not open on port $port"
    }

    $htmlUri = ([System.Uri](Resolve-Path $HtmlPath).Path).AbsoluteUri
    $manifestJson = [System.IO.File]::ReadAllText((Resolve-Path $ManifestJsonPath).Path, [System.Text.Encoding]::UTF8)

    $resJson = [AutoSubCdpRenderer]::Run($wsUrl, $htmlUri, $manifestJson, $OutDir, $Width, $Height)
    Write-Output $resJson
} finally {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 100
    Remove-Item $UserDataDir -Recurse -Force -ErrorAction SilentlyContinue
}
