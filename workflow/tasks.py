"""
workflow/tasks.py — Executable task library for the four-phase pipeline.

Phase 0 ASSET_RECON runs deterministic collection/analysis tasks.
Phase 2 AUTONOMOUS_ATTACK reuses deterministic API/value-linkage helpers.
Phase 1 and Phase 3 are primarily AI/reporter driven.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class TaskStep:
    step: int
    tool: str
    action: str
    instruction: str
    output_file: str = ""
    critical: bool = False


@dataclass
class Task:
    task_id: str
    phase: str
    order: int
    title: str
    steps: list = field(default_factory=list)
    gate_check: str = ""


# ===== Phase 0: COLLECT =====
COLLECT_TASKS = [
    Task("c0_navigate", "collect", 1, "Navigate + screenshot + snow_eyes + JS URL extraction",
         [TaskStep(1, "chrome-devtools", "Navigate, screenshot, list network requests, snow_eyes",
          "1. navigate_page {target}\n2. take_screenshot -> output/{target}/screens/\n3. list_network_requests -> filter resourceType:script -> save URLs to output/{target}/js/_js_urls.txt\n4. evaluate_script -> inject scripts/snow_eyes_inject.js -> save to findings/_snow_eyes.json",
          "js/_js_urls.txt", True)]),

    Task("c0_fingerprint", "collect", 2, "Tech fingerprint + extract JS from HTML",
         [TaskStep(1, "curl", "Get response headers", "curl -sI {target} > findings/_headers.txt", "findings/_headers.txt"),
          TaskStep(2, "curl", "Extract <script src> from HTML", "curl -s {target} | grep -oP 'src=\"[^\"]+\\.js[^\"]*\"' | sort -u > findings/_js_from_html.txt", "findings/_js_from_html.txt")]),

    Task("c0_download_js", "collect", 3, "Download all JS files to local",
         [TaskStep(1, "curl", "Download JS files one by one",
          "cd output/{target}/js\ncat _js_urls.txt ../findings/_js_from_html.txt 2>/dev/null | grep -oP 'https?://[^\"<> ]+\\.js' | sort -u | while read url; do fname=$(echo $url | tr '/:.?=&' '_' | cut -c1-60); curl -s $url -o ${fname}.js 2>/dev/null; done\nls *.js 2>/dev/null | wc -l > _count.txt\necho Downloaded $(cat _count.txt) JS files",
          "js/_count.txt", True)]),

    Task("c0_source_leak", "collect", 4, "GitHub + Gitee source leak search",
         [TaskStep(1, "github", "Search org and code", "search_users({company_name}) -> search_code({domain} .env password api_key secret jwt) -> save findings/_source_leaks.txt", "findings/_source_leaks.txt")]),

    Task("c0_external_assets", "collect", 5, "Resolve DNS and collect authorized subdomains",
         [TaskStep(1, "dns/subdomain", "Resolve target and enumerate in-scope names",
          "Resolve A/AAAA/CNAME/MX/TXT records for {domain}. Use the available passive subdomain tools, keep only names within the authorized scope, and save structured JSON with hostname, record type, value, source, and in_scope fields.",
          "findings/_external_assets.json", True)]),

    Task("c0_exposure_probe", "collect", 6, "Probe Swagger/OpenAPI and common exposure paths",
         [TaskStep(1, "http", "Probe a bounded common-path dictionary",
          "Probe Swagger/OpenAPI endpoints and a bounded set of common diagnostic paths on in-scope HTTP assets. Record URL, status, content type, title or distinctive marker, and redirect target. Do not classify a response as a vulnerability.",
          "findings/_exposure_probe.json", True)]),

    Task("c0_sourcemaps", "collect", 7, "Download referenced JavaScript sourcemaps",
         [TaskStep(1, "python/http", "Discover and download sourcemaps",
          "Read sourceMappingURL directives from every downloaded JS file, resolve relative URLs against the original script URL, download in-scope maps, and save an index containing JS file, map URL, local path, status, and size.",
          "findings/_sourcemaps.json", True)]),
]

# ===== Phase 1: ANALYZE =====
ANALYZE_TASKS = [
    Task("a1_analyze_js", "analyze", 1, "Deep-read JS + call-site tracing for full param signatures.",
         [TaskStep(1, "read", "Read EVERY JS file then trace call sites to extract full param lists", r"""FOR EACH JS file in output/{target}/js/*.js, do ALL steps:

=== STEP A: FIND ALL API ENDPOINT URLS ===
Search for URL patterns in the JS:
  '/api/' '/v1/' '/v2/' '/rest/' '/userCenter/' '/manage/' '/admin/'
  baseURL: API_HOST: serverUrl: endpoint: url:
Also grep: "url:" ':url:' 'path:' 'proxyUrl:' 'base:'

For each URL found, record the surrounding function (the full request call context).

=== STEP B: FOR EACH API CALL, EXTRACT METHOD + PARAM NAMES ===
Identify the HTTP method:
  axios.get(URL, config)           -> method: GET, params in config.params or URL query
  axios.post(URL, data, config)    -> method: POST, params in data object
  axios.put(URL, data)             -> method: PUT
  axios.delete(URL, config)        -> method: DELETE
  fetch(URL, {method:'POST', body:..., headers:...})
  request({url:URL, method:'POST', data:{...}, params:{...}})
  $.ajax / $.post / $.get / http.post / api.post

To extract PARAMETER NAMES from the request body/data:
  [Direct literal]  data: {userId: uid, orgId: orgId, pageNum: 1, pageSize: 10}
    -> extract: userId, orgId, pageNum, pageSize
  [JSON.stringify]  body: JSON.stringify({uid, name, phone})
    -> extract: uid, name, phone
  [Variable ref]  data: params  or  data: formData  or  data: query
    -> SEARCH UPWARD in the same function to find how params/formData/query is built
    -> Look for: params.xxx = ...; Object.assign(params, {...}); {...spread}
  [GET query string]  params: {uid: id, status: 1}  or  URL + '?uid=' + id
    -> extract param names from the params/config.params object

=== STEP C: CALL-SITE TRACE-BACK (this fills params_required/optional) ===
Many apps wrap API calls in helper functions:
  function getUserInfo(data) { return http.post('/user/info', data) }
  export const getUserList = (params) => request({url:'/user/list', method:'post', data:params})

For each wrapper function found, SEARCH ALL JS FILES for call sites:
  Search pattern: functionName(   or   functionName({

At each call site, extract the OBJECT SHAPE being passed:
  getUserInfo({userId: row.id, orgId: currentOrg})
    -> /user/info params: userId, orgId
  getUserList({pageNum: 1, pageSize: 20, accountName: keyword})
    -> /user/list params: pageNum, pageSize, accountName

=== STEP D: EXTRACT CONTENT-TYPE + AUTH ===
Content-Type: check headers in the call, or infer:
  body uses JSON.stringify or {key:val} literal  -> application/json
  body uses FormData or new URLSearchParams      -> application/x-www-form-urlencoded
  GET/DELETE with no body                        -> empty (no Content-Type)

Auth: check for 'Authorization', 'X-API-Key', 'X-Auth-Token', 'Bearer', 'token' in:
  - The individual API call's headers/config
  - axios/fetch request interceptors (axios.interceptors.request.use)
  - The base axios.create({headers:{...}}) config

=== STEP D2: EXTRACT LOGIN LINKS FOR CREDENTIAL GATE ===
Find login/account entry points so any future request for test accounts includes the exact link:
  - Routes or paths containing login, signin, sso, oauth, auth, register, callback
  - HTML form action targets for login forms
  - 302 Location values that point to login/SSO
  - OAuth authorize URLs and SSO redirect URLs
Record full URL when base_url is known; otherwise record path + source file.

=== STEP E: SAVE PER-FILE ANALYSIS ===
Save to findings/_analysis_{filename}.json:
{
  "analyzed": true,
  "filename": "app.js",
  "size_kb": <number>,
  "classification": "app|admin|chunk|vendor|config|login|unknown",
  "priority": "P0|P1|P2|P3",
  "base_url": "<extracted baseURL or empty>",
  "endpoints": [
    {
      "url": "/userCenter/userManager/user/list",
      "method": "POST",
      "content_type": "application/json",
      "auth": "none|Bearer|X-API-Key|Cookie",
      "params_required": ["pageNum", "pageSize"],
      "params_optional": ["accountName"],
      "source_files": ["app.js"],
      "notes": "traced from getUserList({pageNum:1,pageSize:10,accountName:x}) call site"
    }
  ],
  "secrets": [
    {"type": "apiKey|jwt_secret|password|cloud_key", "key": "var_name", "value": "xxx"}
  ],
  "login_links": [
    {"url": "/#/login", "type": "spa_route", "source": "app.js", "confidence": "high"}
  ],
  "interceptors": "summary of any axios/fetch interceptors found"
}

=== STEP F: CLASSIFICATION ===
P0 (admin API): contains /admin/ /manage/ /boss/ /console/ /system/ /platform/ URLs
P1 (user API): contains /user/ /order/ /api/ URLs, no admin URLs
P2 (vendor with config): known lib file BUT has axios.create/baseURL config
P3 (pure vendor): confirmed 3rd-party library, no API endpoints

=== STEP G: HARD RULES ===
- Every file must be READ fully, not just grep'd
- params_required/params_optional MUST come from call-site tracing
- If same endpoint appears in multiple files -> merge param lists
- method MUST NOT be empty string
- source_files MUST list which file(s) the endpoint was extracted from
- Hex-encoded strings (\xNN) -> decode with python first
"""
          "findings/_analysis_summary.md", True)]),

    Task("a2_build_params", "analyze", 99, "Build _endpoint_params.json with completeness gate check",
         [TaskStep(1, "python", "Aggregate analysis files, run shared.linkage gate check", r"""import json, os, glob, sys

SKILL_ROOT = os.environ.get("MASTERMIND_ROOT", os.getcwd())
if SKILL_ROOT not in sys.path:
    sys.path.insert(0, SKILL_ROOT)

hunt_dir = "output/{target}"
analysis_files = glob.glob(hunt_dir + "/findings/_analysis_*.json")
total_js = len(glob.glob(hunt_dir + "/js/*.js"))

all_endpoints = {}
all_secrets = []
login_links = []
files_detail = {}
analyzed_count = 0

for af in analysis_files:
    data = json.loads(open(af).read())
    fname = data.get("filename", os.path.basename(af))
    if data.get("analyzed"):
        analyzed_count += 1
        files_detail[fname] = {
            "analyzed": True,
            "api_calls_found": len(data.get("endpoints", [])),
            "classification": data.get("classification", "unknown"),
            "priority": data.get("priority", "P1"),
            "notes": data.get("notes", ""),
        }
        for ep in data.get("endpoints", []):
            url = ep["url"]
            if url not in all_endpoints:
                all_endpoints[url] = {
                    "method": ep.get("method", ""),
                    "content_type": ep.get("content_type", ""),
                    "auth": ep.get("auth", ""),
                    "params_required": ep.get("params_required", []),
                    "params_optional": ep.get("params_optional", []),
                    "source_files": ep.get("source_files", [fname]),
                    "notes": ep.get("notes", ""),
                }
            else:
                for sf in ep.get("source_files", []):
                    if sf not in all_endpoints[url]["source_files"]:
                        all_endpoints[url]["source_files"].append(sf)
        all_secrets.extend(data.get("secrets", []))
        for link in data.get("login_links", []):
            if link not in login_links:
                login_links.append(link)

# Build v2.4 format with _meta + endpoints
output = {
    "_meta": {
        "js_files_collected": total_js,
        "js_files_analyzed": analyzed_count,
        "js_files_skipped": [],
        "skipped_reason": "",
        "analysis_completeness": round(analyzed_count / max(total_js, 1), 2),
        "files_detail": files_detail,
        "total_endpoints_extracted": len(all_endpoints),
        "total_secrets_found": len(all_secrets),
        "total_routes_found": 0,
        "warnings": [],
        "generated_at": "",
    },
    "endpoints": all_endpoints,
}

os.makedirs(hunt_dir + "/findings", exist_ok=True)
json.dump(output, open(hunt_dir + "/findings/_endpoint_params.json", "w"), indent=2, ensure_ascii=False)
json.dump({"login_links": login_links}, open(hunt_dir + "/findings/_login_links.json", "w"), indent=2, ensure_ascii=False)

# Run the actual gate check from shared/linkage.py
from shared.linkage import check_js_analysis_completeness
gate_result = check_js_analysis_completeness(output)
print(gate_result.summary)

if not gate_result.passed:
    print("\n*** PHASE 0 GATE BLOCKED — fix the issues above before proceeding ***")
    for f in gate_result.failures:
        print("  FAIL:", f)
else:
    print("\nPhase 0 Gate: PASSED — ready for Phase 1")
""", "findings/_endpoint_params.json", True)]),
]

# ===== Phase 2: TEST =====
TEST_TASKS = [
    Task("t0_baseurl", "test", 1, "Determine base URL (same-origin fallback if no explicit baseUrl)",
         [TaskStep(1, "python", "Extract base URL", """import json
eps = json.loads(open("output/{target}/findings/_endpoint_params.json").read())
base = eps.get("_meta", {}).get("base_url", "")
if not base:
    for url in eps.get("endpoints", {}):
        if url.startswith("http"):
            from urllib.parse import urlparse
            p = urlparse(url)
            base = p.scheme + "://" + p.netloc
            break
if not base:
    base = "{target}"
open("output/{target}/findings/_base_url.txt", "w").write(base)
print("baseUrl =", base)
""", "findings/_base_url.txt", True)]),

    Task("t1_blind", "test", 2, "BLIND PROBE: 6 common JSON body variants + GET all endpoints",
         [TaskStep(1, "python", "Generate curl blind probe with 6 body variants", r"""import json
BASE = open("output/{target}/findings/_base_url.txt").read().strip()
eps = json.loads(open("output/{target}/findings/_endpoint_params.json").read())
lines = ["#!/bin/bash", "echo BlindProbe $(date)"]

# 6 common JSON body variants for POST endpoints
bodies = [
    ("POST_empty", "{}"),
    ("POST_pageNum", '{"pageNum":1,"pageSize":10}'),
    ("POST_page", '{"page":1,"size":10}'),
    ("POST_current", '{"current":1,"pageSize":10}'),
    ("POST_pageNo", '{"pageNo":1,"pageSize":10}'),
    ("POST_all", '{"pageNum":1,"pageSize":10,"page":1,"size":10,"current":1,"pageNo":1,"pageSize":10,"limit":10,"pageIndex":1}'),
]

for url, info in eps.get("endpoints", {}).items():
    ep = url if url.startswith("/") else "/" + url.split("/", 3)[-1] if "://" in url else url
    ct = info.get("content_type", "application/json")
    
    for label, body in bodies:
        lines.append("echo '>>> " + label + " " + ep + "'")
        lines.append("curl -s -w 'HTTP_CODE:%{http_code}' -X POST '" + BASE + ep + "' -H 'Content-Type: " + ct + "' -d '" + body + "' 2>&1")
    
    lines.append("echo '>>> GET " + ep + "'")
    lines.append("curl -s -w 'HTTP_CODE:%{http_code}' '" + BASE + ep + "?uid=test' 2>&1")

lines.append("echo DONE")
import os
os.makedirs("output/{target}/scripts", exist_ok=True)
open("output/{target}/scripts/_blind_probe.sh", "w").write("\n".join(lines))
print("Generated:", len(eps.get("endpoints", {})), "endpoints x 7 probes each")
""", "scripts/_blind_probe.sh", True),
          TaskStep(2, "bash", "Execute blind probe", "bash output/{target}/scripts/_blind_probe.sh 2>&1 | tee output/{target}/findings/_blind_results.txt", "findings/_blind_results.txt", True)]),

    Task("t1.5_param_hunt", "test", 2.5, "Parameter hunt: 500 errors -> scan hints -> uid/Uid/userId variants -> test with curl",
         [TaskStep(1, "python", "Hunt correct param names from 500 error messages, try all variants",
          r"""import json, re, subprocess

BASE = open("output/{target}/findings/_base_url.txt").read().strip()
blind = open("output/{target}/findings/_blind_results.txt").read()
hints = []; cur = ""
for line in blind.split("\n"):
    if line.startswith(">>>"): cur = line.split()[-1] if line.split() else ""
    elif "HTTP_CODE:500" in line or "HTTP_CODE:400" in line:
        idx = blind.index(line); prev = blind[max(0,idx-300):idx]
        m = re.search(r'["\x27]([a-zA-Z_]\w{0,30})["\x27](?:不能为空|is required|must not be|参数|null)', prev)
        if m: hints.append({"ep": cur, "hint": m.group(1), "err": prev[-60:]})

VM = {"uid":["uid","Uid","UID","userId","user_id","userid","id","ID"],
      "Uid":["uid","Uid","UID","userId","user_id","userid","id","ID"],
      "userId":["userId","user_id","userid","uid","Uid","UID","id","ID"],
      "id":["id","ID","Id","uid","Uid","userId"],
      "pageNum":["pageNum","page","pageNo","pageIndex","current"], "pageSize":["pageSize","limit","size","page_size"],
      "default":["id","ID","uid","Uid","userId","user_id","pageNum","page","pageSize","limit"]}
results = []
for h in hints:
    ep = h["ep"]; vs = VM.get(h["hint"], VM.get(h["hint"].lower(), VM["default"]))
    for v in vs[:6]:
        # POST JSON
        body = json.dumps({v:"test_v"})
        cmd = ["curl","-s","-w","HTTP_CODE:%{http_code}","-X","POST",BASE+ep,"-H","Content-Type: application/json","-d",body]
        try:
            out = subprocess.check_output(cmd,timeout=10,stderr=subprocess.STDOUT).decode()
            code = out.split("HTTP_CODE:")[-1].strip(); pre = out.split("HTTP_CODE:")[0][:120]
            hit = "200" in code
            partial = "500" in code and "不能为空" not in pre and "is required" not in pre.lower() and "must not" not in pre.lower()
            if hit or partial:
                results.append({"ep":ep,"param":v,"status":code,"hit":hit}); print("HIT" if hit else "MAYBE",ep,v,"->",code)
                if hit: break
        except: pass
        # GET
        cmd2 = ["curl","-s","-w","HTTP_CODE:%{http_code}",BASE+ep+"?"+v+"=test_v"]
        try:
            out2 = subprocess.check_output(cmd2,timeout=10,stderr=subprocess.STDOUT).decode()
            if "200" in out2.split("HTTP_CODE:")[-1].strip():
                results.append({"ep":ep,"param":v,"status":"200","hit":True,"method":"GET"}); print("HIT GET",ep,v); break
        except: pass

if results:
    ep_path = "output/{target}/findings/_endpoint_params.json"
    eps = json.loads(open(ep_path).read())
    for r in results:
        if r.get("hit") and r["ep"] in eps.get("endpoints",{}):
            ei = eps["endpoints"][r["ep"]]
            if r.get("method")=="GET": ei["method"] = "GET"
            if r["param"] not in ei.get("params_required",[]): ei.setdefault("params_required",[]).append(r["param"])
    json.dump(eps, open(ep_path,"w"), indent=2, ensure_ascii=False)
json.dump(results, open("output/{target}/findings/_param_hunt.json","w"), indent=2)
print("Param hunt:", len([r for r in results if r.get("hit")]), "hits,", len(results), "total")
""",
          "findings/_param_hunt.json", True)]),

    Task("t2_mine", "test", 3, "Mine 200 responses -> leaked values pool (v2.4 with consumption tracking)",
         [TaskStep(1, "python", "Extract field names and values from 200 responses, produce v2.4 ValuePool format", r"""import json, re, os
from datetime import datetime, timezone

hunt_dir = "output/{target}"
content = open(hunt_dir + "/findings/_blind_results.txt").read()
now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# v2.4 pool format: param_name -> { "values": [ {value, status, discovered_at, source_endpoint, source_param, priority, consumed_endpoints, unconsumed_endpoints} ] }
pool = {}
current_ep = ""
current_method = ""

SENSITIVE_KEYWORDS = (
    "uid", "userid", "user_id", "token", "accesstoken", "refreshtoken",
    "password", "pwd", "secret", "apikey", "api_key", "privatekey",
    "role", "isadmin", "phone", "mobile", "email", "orgid", "org_id",
    "tenantid", "orderid", "akid", "akia", "ltai", "aiza"
)

for line in content.split("\n"):
    if line.startswith(">>>"):
        parts = line.split()
        if len(parts) >= 2:
            current_method = parts[1] if parts[1] in ("POST", "GET", "PUT", "DELETE", "PATCH") else ""
            current_ep = parts[-1] if parts else ""
        else:
            current_ep = parts[-1] if parts else ""
    elif "HTTP_CODE:200" in line:
        idx = content.index(line)
        prev = content[max(0, idx - 500):idx]
        js_match = re.search(r'\{.*\}', prev, re.DOTALL)
        if js_match:
            try:
                data = json.loads(js_match.group())
                result = data.get("result", data) if isinstance(data, dict) else data
                items_to_mine = []
                if isinstance(result, dict):
                    items_to_mine = [(k, v) for k, v in result.items() if v is not None]
                elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
                    for item in result[:3]:
                        items_to_mine.extend([(k, v) for k, v in item.items() if v is not None])
                
                for k, v in items_to_mine:
                    k_lower = k.lower()
                    priority = "HIGH" if any(p in k_lower for p in SENSITIVE_KEYWORDS) else "MEDIUM"
                    if k not in pool:
                        pool[k] = {"values": []}
                    # Dedup by value string
                    existing_vals = [ve["value"] if isinstance(ve, dict) else ve for ve in pool[k]["values"]]
                    if str(v) not in existing_vals:
                        pool[k]["values"].append({
                            "value": str(v),
                            "status": "pending",
                            "discovered_at": now_ts,
                            "source_endpoint": current_ep,
                            "source_param": k,
                            "priority": priority,
                            "consumed_endpoints": [],
                            "unconsumed_endpoints": [],
                        })
            except: pass

os.makedirs(hunt_dir + "/findings", exist_ok=True)
json.dump(pool, open(hunt_dir + "/findings/_leaked_values.json", "w"), indent=2, ensure_ascii=False)
high = sum(1 for v in pool.values() for ve in v["values"] if isinstance(ve, dict) and ve.get("priority") == "HIGH")
total_vals = sum(len(v["values"]) for v in pool.values())
print("Value pool:", len(pool), "fields,", total_vals, "values (", high, "HIGH priority)")
for k, v in sorted(pool.items()):
    vals = v["values"]
    priorities = set(ve.get("priority", "?") if isinstance(ve, dict) else "?" for ve in vals)
    src = vals[0].get("source_endpoint", "?") if vals else "?"
    print(" ", k, ":", len(vals), "values [", ",".join(sorted(priorities)), "] src:", src)
""", "findings/_leaked_values.json", True)]),

    Task("t3_linkage", "test", 4, "VALUE POOL x ENDPOINT PARAMS -> PairingEngine (41 aliases) + full method fallback matrix",
         [TaskStep(1, "python", "Generate linkage pairs via PairingEngine with semantic expansion", r"""import json, sys, os
hunt_dir = "output/{target}"

SKILL_ROOT = os.environ.get("MASTERMIND_ROOT", os.getcwd())
if SKILL_ROOT not in sys.path:
    sys.path.insert(0, SKILL_ROOT)

from shared.linkage import PairingEngine, EndpointRegistry, ValuePool

ep_path = hunt_dir + "/findings/_endpoint_params.json"
vp_path = hunt_dir + "/findings/_leaked_values.json"

if not os.path.exists(ep_path):
    print("ERROR: _endpoint_params.json not found at", ep_path)
    print("Run ANALYZE phase first.")
    exit(1)

pool = ValuePool.from_file(vp_path) if os.path.exists(vp_path) else ValuePool()
registry = EndpointRegistry.from_file(ep_path)
engine = PairingEngine(registry, pool)
engine.sync_consumption_state()
pairs = engine.match(semantic_expand=True)

pairs_json = []
for p in pairs:
    pairs_json.append({
        "ep": p.endpoint, "method": p.method,
        "fallback_methods": p.fallback_methods,
        "param": p.param_name, "value": p.value_entry.value,
        "priority": p.priority, "status": p.value_entry.status.value,
        "consumed_endpoints": p.value_entry.consumed_endpoints,
    })

os.makedirs(hunt_dir + "/findings", exist_ok=True)
json.dump(pairs_json, open(hunt_dir + "/findings/_linkage_pairs.json", "w"), indent=2, ensure_ascii=False)

by_priority = {}
for p in pairs_json:
    pri = p["priority"]
    by_priority[pri] = by_priority.get(pri, 0) + 1
print("Linkage pairs:", len(pairs_json), by_priority)
print("  (PairingEngine: 41 param aliases + 4 semantic groups)")
for p in pairs_json[:10]:
    tag = " [UNCONSUMED]" if p["status"] != "consumed" else ""
    print("  [" + p["priority"] + "]", p["method"], p["ep"], p["param"] + "=" + str(p["value"]) + tag)
if len(pairs_json) > 10:
    print("  ... and", len(pairs_json) - 10, "more")
""", "findings/_linkage_pairs.json", True),
         TaskStep(2, "python", "Execute linkage + MINE hit responses + LOOP until saturation (max 3 rounds)", r"""import json, subprocess, sys, os, re
from datetime import datetime, timezone

SKILL_ROOT = os.environ.get("MASTERMIND_ROOT", os.getcwd())
if SKILL_ROOT not in sys.path:
    sys.path.insert(0, SKILL_ROOT)
from shared.linkage import (
    build_method_fallback_matrix, ValuePool,
    EndpointRegistry, PairingEngine, canonical_param_name
)

hunt_dir = "output/{target}"
BASE = open(hunt_dir + "/findings/_base_url.txt").read().strip()

# Load state
vp_path = hunt_dir + "/findings/_leaked_values.json"
ep_path = hunt_dir + "/findings/_endpoint_params.json"
pool = ValuePool.from_file(vp_path) if os.path.exists(vp_path) else ValuePool()
registry = EndpointRegistry.from_file(ep_path)

SENSITIVE_KEYWORDS = (
    "uid", "userid", "user_id", "token", "accesstoken", "refreshtoken",
    "password", "pwd", "secret", "apikey", "api_key", "privatekey",
    "role", "isadmin", "phone", "mobile", "email", "orgid", "org_id",
    "tenantid", "orderid", "akid", "akia", "ltai", "aiza"
)

# ── HTTP sender (returns full body) ──
def send(method, ep, param, val, content_type=None):
    if method in ("GET", "DELETE", "OPTIONS", "HEAD"):
        cmd = ["curl", "-s", "-w", "HTTP_CODE:%{http_code}",
               "-X", method, BASE + ep + "?" + param + "=" + str(val)]
    elif content_type == "multipart/form-data":
        cmd = ["curl", "-s", "-w", "HTTP_CODE:%{http_code}",
               "-X", method, BASE + ep, "-F", param + "=" + str(val)]
    else:
        ct = content_type or "application/json"
        body = json.dumps({param: str(val)}) if "json" in ct else param + "=" + str(val)
        cmd = ["curl", "-s", "-w", "HTTP_CODE:%{http_code}",
               "-X", method, BASE + ep, "-H", "Content-Type: " + ct, "-d", body]
    try:
        out = subprocess.check_output(cmd, timeout=10, stderr=subprocess.STDOUT).decode()
        if "HTTP_CODE:" in out:
            body_part = out.rsplit("HTTP_CODE:", 1)[0]
            code_str = out.rsplit("HTTP_CODE:", 1)[1].strip()
        else:
            body_part, code_str = out, "0"
        code = int(code_str) if code_str.isdigit() else 0
        return code, body_part
    except Exception as e:
        return -1, str(e)[:100]

# ── Response miner (same logic as t2_mine) ──
def mine_response(response_body, source_ep):
    # Extract field->value pairs from JSON response. Returns list of dicts.
    new_vals = []
    try:
        data = json.loads(response_body)
        result = data.get("result", data) if isinstance(data, dict) else data
        items = []
        if isinstance(result, dict):
            items = [(k, v) for k, v in result.items() if v is not None]
        elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
            for item in result[:3]:
                items.extend([(k, v) for k, v in item.items() if v is not None])
        for k, v in items:
            k_lower = k.lower()
            prio = "HIGH" if any(p in k_lower for p in SENSITIVE_KEYWORDS) else "MEDIUM"
            existing = pool.get_values(k)
            if not any(e.value == str(v) for e in existing):
                pool.add_value(k, str(v), source_endpoint=source_ep,
                               source_param=k, priority=prio)
                new_vals.append({"param": k, "value": str(v), "priority": prio})
    except:
        pass
    return new_vals

# ── Error-driven param discovery (learn params from 400/500 error messages) ──
def learn_params_from_error(response_body, ep):
    # Extract missing parameter name from error message. Returns (param_name, values_to_try).
    if not response_body or len(response_body) > 2000:
        return None, []
    # Chinese error patterns
    m = re.search(r'[\"\\x27]([a-zA-Z_]\\w{0,30})[\"\\x27](?:不能为空|is required|must not be|参数)', response_body)
    if not m:
        m = re.search(r'(?:parameter|Param|field|Field)\\s+[\"\\x27]?(\\w{1,30})[\"\\x27]?\\s+(?:is required|missing|invalid)', response_body, re.I)
    if not m:
        m = re.search(r'缺少参数[\"\\x27]?(\\w{1,30})', response_body)
    if not m:
        return None, []
    param_name = m.group(1)
    # Update endpoint registry with newly discovered required param
    req = registry.get(ep)
    if req:
        if param_name not in req.params_required and param_name not in req.params_optional:
            req.params_required.append(param_name)
            print(\"    +LEARNED param [{}] for {} from error message\".format(param_name, ep))
    # Check if value pool already has values for this param
    existing = pool.get_values(param_name)
    vals = [e.value for e in existing if e.status.value != \"consumed\"]
    if vals:
        print(\"    +POOL has {} values for {} -> will inject next\".format(len(vals), param_name))
    return param_name, vals

# ── LINKAGE LOOP ──
MAX_ROUNDS = 3
all_results = []
round_num = 0
total_new_values = 1

print("Value pool start:", sum(1 for _ in pool.all_entries()), "entries")
print("Endpoints:", len(registry.all_endpoints()))
print()

while total_new_values > 0 and round_num < MAX_ROUNDS:
    round_num += 1
    print("=== LINKAGE ROUND", round_num, "/", MAX_ROUNDS, "===")

    # Re-pair with current pool state
    engine = PairingEngine(registry, pool)
    engine.sync_consumption_state()
    pairs = engine.match(semantic_expand=True)

    # Only test unconsumed pairs
    untested = [p for p in pairs if p.value_entry.status.value != "consumed"]
    print("Pairs:", len(pairs), "total,", len(untested), "untested")

    if not untested:
        print("No untested pairs -- linkage saturated")
        break

    round_new_values = []
    round_hits = 0
    total = len(untested)

    for i, p in enumerate(untested):
        ep = p.endpoint
        param = p.param_name
        val = str(p.value_entry.value)
        method = p.method
        priority = p.priority

        status_code, body = send(method, ep, param, val, "application/json")
        hit = 200 <= status_code < 300
        method_used = method

        # Method fallback on non-2xx trigger codes
        if not hit and status_code in (405, 500, 415, 400, 501, -1):
            matrix = build_method_fallback_matrix(ep, method,
                          status_code if status_code > 0 else 500)
            for fb in matrix[:12]:
                fb_code, fb_body = send(fb["method"], ep, param, val,
                                        fb.get("content_type"))
                if 200 <= fb_code < 300:
                    status_code, body, hit, method_used = (
                        fb_code, fb_body, True, fb["method"])
                    break

        if hit:
            round_hits += 1
            print("  HIT [{}] {} {} {}={} -> {}".format(
                priority, method_used, ep, param, val, status_code))

            # ★ MINE the response for new values ★
            new_vals = mine_response(body, ep)
            round_new_values.extend(new_vals)
            for nv in new_vals:
                print("    +NEW [{}] {}={}".format(
                    nv["priority"], nv["param"], nv["value"]))

            pool.mark_consumed(param, val, ep)

            # Save full response body for evidence
            os.makedirs(hunt_dir + "/findings/_linkage_bodies", exist_ok=True)
            fname = ep.replace("/", "_") + "_" + param + "_" + val[:20]
            fname = re.sub(r'[^a-zA-Z0-9_-]', '_', fname)[:80]
            with open(hunt_dir + "/findings/_linkage_bodies/" + fname + ".json", "w") as f:
                try:
                    json.dump(json.loads(body), f, indent=2, ensure_ascii=False)
                except:
                    f.write(body)
        else:
            pool.mark_consumed(param, val, ep)
            # ★ Try to learn missing params from error messages ★
            if status_code in (400, 500):
                learned_param, pool_vals = learn_params_from_error(body, ep)
                if learned_param and pool_vals:
                    # Value pool already has values for this param → inject now
                    for pv in pool_vals:
                        lc, lb = send(method_used, ep, learned_param, pv)
                        if 200 <= lc < 300:
                            round_hits += 1
                            print("  HIT [LEARNED] {} {} {}={} -> {}".format(
                                method_used, ep, learned_param, pv, lc))
                            nv2 = mine_response(lb, ep)
                            round_new_values.extend(nv2)
                            for nv in nv2:
                                print("    +NEW [{}] {}={}".format(
                                    nv["priority"], nv["param"], nv["value"]))
                            pool.mark_consumed(learned_param, pv, ep)
                            all_results.append({
                                "ep": ep, "param": learned_param, "value": pv,
                                "method": method_used, "status": str(lc),
                                "hit": True, "round": round_num,
                            })

        all_results.append({
            "ep": ep, "param": param, "value": val,
            "method": method_used, "status": str(status_code),
            "hit": hit, "round": round_num,
        })

        if (i + 1) % 10 == 0:
            print("  Progress: {}/{}".format(i + 1, total))

    total_new_values = len(round_new_values)
    print("Round {}: {} hits, {} new values added to pool\n".format(
        round_num, round_hits, total_new_values))

    if total_new_values == 0:
        print("No new values discovered -- linkage saturated")

# ── Save results ──
json.dump(all_results, open(hunt_dir + "/findings/_linkage_results.json", "w"),
          indent=2, ensure_ascii=False)
pool.to_file(vp_path)

total_hits = sum(1 for r in all_results if r["hit"])
print("Linkage complete: {}/{} hits across {} rounds".format(
    total_hits, len(all_results), round_num))

# Pool growth summary
entries = list(pool.all_entries())
print("Value pool:", sum(1 for _ in entries), "entries")
by_prio = {}
for _, e in entries:
    by_prio[e.priority] = by_prio.get(e.priority, 0) + 1
print("  By priority:", by_prio)
unconsumed = sum(1 for _, e in entries
                 if e.status.value in ("pending", "consuming"))
if unconsumed:
    print("WARN:", unconsumed, "value entries still pending/consuming")
""", "findings/_linkage_results.json", True)]),

    Task("t4_candidates", "test", 5, "Aggregate candidate findings for verification",
         [TaskStep(1, "python", "Aggregate signals into candidate findings", r"""import json, os
hunt_dir = "output/{target}"
findings_dir = hunt_dir + "/findings"

BASE = open(findings_dir + "/_base_url.txt").read().strip()
blind = open(findings_dir + "/_blind_results.txt").read() if os.path.exists(findings_dir + "/_blind_results.txt") else ""
linkage = json.load(open(findings_dir + "/_linkage_results.json")) if os.path.exists(findings_dir + "/_linkage_results.json") else []
pool = json.load(open(findings_dir + "/_leaked_values.json")) if os.path.exists(findings_dir + "/_leaked_values.json") else {}

candidates = []

# Blind probe: unauthenticated 200 responses with data
lines = blind.split("\n")
cur = ""
for i, line in enumerate(lines):
    if line.startswith(">>>"):
        cur = " ".join(line.split()[1:3])
    elif "HTTP_CODE:200" in line:
        prev = "\n".join(lines[max(0, i-3):i])
        if "{" in prev and ('"code":0' in prev or '"total"' in prev or '"records"' in prev):
            candidates.append({"vuln_class": "Unauthenticated Data Access", "target_url": cur, "evidence": prev[:200], "impact": "", "poc_steps": [], "confidence": 0.5, "severity": "medium"})

# Linkage hits
for r in linkage:
    if r.get("hit"):
        candidates.append({"vuln_class": "IDOR/Data Leak", "target_url": r["ep"], "evidence": r.get("preview", ""), "impact": "", "poc_steps": [], "confidence": 0.6, "severity": "high", "context": {"param": r["param"], "value": r["value"]}})

# Sensitive fields in value pool (handle v2.4 format)
for k, v in pool.items():
    vals = v.get("values", [])
    for ve in vals:
        if isinstance(ve, dict) and ve.get("priority") == "HIGH":
            candidates.append({"vuln_class": "Sensitive Field Exposure", "target_url": ve.get("source_endpoint", ""), "evidence": "Observed high-priority field: " + k, "impact": "", "poc_steps": [], "confidence": 0.5, "severity": "medium", "context": {"field": k, "value": ve.get("value", "")}})

json.dump({"candidates": candidates}, open(findings_dir + "/_candidate_findings.json", "w"), indent=2, ensure_ascii=False)
print("Candidates:", len(candidates), "->", findings_dir + "/_candidate_findings.json")
print("These are signals only. Add reproducible impact and PoC evidence before Verifier review.")
""", "findings/_candidate_findings.json", True)]),

    Task("t5_gate", "test", 99, "Pair Completeness Gate: verify no HIGH/CRITICAL values remain unconsumed",
         [TaskStep(1, "python", "Run check_pair_completeness from shared/linkage.py", r"""import json, sys, os

SKILL_ROOT = os.environ.get("MASTERMIND_ROOT", os.getcwd())
if SKILL_ROOT not in sys.path:
    sys.path.insert(0, SKILL_ROOT)

from shared.linkage import (
    PairingEngine, EndpointRegistry, ValuePool,
    check_pair_completeness, save_linkage_state
)

hunt_dir = "output/{target}"
ep_path = hunt_dir + "/findings/_endpoint_params.json"
vp_path = hunt_dir + "/findings/_leaked_values.json"

if not os.path.exists(ep_path) or not os.path.exists(vp_path):
    print("WARN: Missing endpoint params or value pool — skipping gate check")
    exit(0)

registry = EndpointRegistry.from_file(ep_path)
pool = ValuePool.from_file(vp_path)
engine = PairingEngine(registry, pool)
engine.sync_consumption_state()
pairs = engine.match(semantic_expand=True)

check = check_pair_completeness(pairs, block_on_critical=True)
print(check.summary)

if check.block_transition:
    print("\n*** GATE BLOCKED: Phase transition halted ***")
    print("Reason:", len(check.critical_unconsumed), "CRITICAL/HIGH value-endpoint pairs are unconsumed.")
    print("These values MUST be tested before entering the next phase:")
    for p in check.critical_unconsumed[:10]:
        print("  - [" + p.priority + "]", p.param_name + "=" + p.value_entry.value, "@", p.endpoint, "[" + p.method + "]")
    if len(check.critical_unconsumed) > 10:
        print("  ... and", len(check.critical_unconsumed) - 10, "more")
    
    # Write unconsumed pairs for forced consumption
    unconsumed_list = []
    for p in check.unconsumed:
        unconsumed_list.append({
            "endpoint": p.endpoint,
            "param": p.param_name,
            "value": p.value_entry.value,
            "method": p.method,
            "fallback_methods": p.fallback_methods,
            "priority": p.priority,
            "reason": p.reason,
        })
    json.dump(unconsumed_list, open(hunt_dir + "/findings/_unconsumed_pairs.json", "w"), indent=2, ensure_ascii=False)
    print("\nUnconsumed pairs saved to", hunt_dir + "/findings/_unconsumed_pairs.json")
    print("RE-RUN t3_linkage to consume these before proceeding.")
    exit(1)
else:
    print("\nPair Completeness Gate: PASSED — all values consumed, safe to proceed")
    save_linkage_state(hunt_dir, pool)
""", "findings/_unconsumed_pairs.json", True)]),
]

PHASE_TASKS = {
    "asset_recon": COLLECT_TASKS + ANALYZE_TASKS,
    "attack_surface_analysis": [
        Task("p1_attack_surface_plan", "attack_surface_analysis", 1,
             "Produce the ranked attack-surface plan",
             [TaskStep(1, "ai", "Analyze reconnaissance without active testing",
              "Read Phase 0 outputs and write findings/_attack_surfaces.json. Each item must contain id, surface, hypothesis, evidence, confidence, impact, exploitability, priority_score, planned_test, and chain_links. Sort descending by priority_score. This phase must not send attack requests.",
              "findings/_attack_surfaces.json", True)])
    ],
    "autonomous_attack": TEST_TASKS,
    "report_generation": [
        Task("p3_verified_report", "report_generation", 1,
             "Generate reports from Verifier-approved findings only",
             [TaskStep(1, "report", "Render the fixed evidence-based report",
              "Read findings/_verified_findings.json. Generate reports/final_report.md with one section per approved finding: title, vulnerability type, severity, URL, reproduction steps, evidence, and remediation. If none are approved, generate a short no-confirmed-findings report. Never read candidates directly.",
              "reports/final_report.md", True)])
    ],
}

# Keep old keys for backward compatibility with pre-four-phase hunt states.
PHASE_TASKS["recon"] = COLLECT_TASKS + ANALYZE_TASKS
PHASE_TASKS["api_fuzz"] = TEST_TASKS
PHASE_TASKS["dependency_scan"] = []
PHASE_TASKS["crypto_attack"] = []
PHASE_TASKS["bypass"] = []
PHASE_TASKS["exploit"] = []
PHASE_TASKS["ai_security"] = []
PHASE_TASKS["collect"] = COLLECT_TASKS
PHASE_TASKS["analyze"] = ANALYZE_TASKS
PHASE_TASKS["test"] = TEST_TASKS

def get_tasks_for_phase(name):
    """Get deterministic tasks for a phase."""
    return PHASE_TASKS.get(name, [])

def count_all_steps():
    return sum(len(t.steps) for ts in PHASE_TASKS.values() for t in ts)
