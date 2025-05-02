import aiohttp
import asyncio
import random
import string
import argparse
import json
import time
import traceback # Import for debug mode
from uuid import uuid4

# --- Constants and Global Config ---

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14; RMX3834 Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/135.0.7049.100 Mobile Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'sec-ch-ua-platform': '"Android"',
    'sec-ch-ua': '"Android WebView";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    # Adding extra sec-ch-ua header variations seen in Jaya cURL, potentially harmless for others
    'sec-ch-ua-full-version-list': '"Android WebView";v="135.0.7049.100", "Not-A.Brand";v="8.0.0.0", "Chromium";v="135.0.7049.100"',
    # Adding x-requested-with, seen in Jaya GET cURL, might be needed by some APIs
    'x-requested-with': 'com.jaya9.jaya9', # Note: This might need adjustment if other apps are targeted
}
POST_HEADERS_BASE = {**DEFAULT_HEADERS, 'Content-Type': 'application/json'}


# --- API Definitions ---
# Add "active": True (to run) or "active": False (to skip) to each config
API_CONFIGS = [
    {
        "name": "Tech",
        "base_url": "https://feapi.bigape88.xyz/api/member",
        "domain": "https://bigtaka.app",
        "referral_code": "bigtaka",
        "registration_needs_captcha": False,
        "origin": "https://bigtaka.app",
        "active": False
    },
    {
        "name": "Babu",
        "base_url": "https://getbombus562i.897909.com/api/member",
        "domain": "https://www.897909.com",
        "referral_code": "",
        "registration_needs_captcha": True,
        "origin": "https://www.897909.com",
        "active": False
    },
    {
        "name": "Crazy",
        "base_url": "https://feapi.unicorn88.xyz/api/member",
        "domain": "https://bhaggo.net",
        "referral_code": "",
        "registration_needs_captcha": False,
        "origin": "https://bhaggo.net",
        "active": False
    },
    {
        "name": "Star",
        "base_url": "https://feluckystar.turtle888.xyz/api/member",
        "domain": "https://1009687.com",
        "referral_code": "",
        "registration_needs_captcha": True,
        "origin": "https://1009687.com",
        "active": False
    },
    {
        "name": "Jaya",
        "base_url": "https://aa7813910.com/api/member",
        "domain": "https://aa7813910.com",
        "referral_code": "",
        "registration_needs_captcha": True, # Needs captcha for registration
        "origin": "https://aa7813910.com",
        "active": False
    },
    {
        "name": "Khela",
        "base_url": "https://feapi.iceage888.xyz/api/member",
        "domain": "https://www.716b33in.com",
        "referral_code": "",
        "registration_needs_captcha": True, # Needs captcha for registration
        "origin": "https://www.716b33in.com",
        "active": False
    },
    { # Added Krikya API
        "name": "Krikya",
        "base_url": "https://feapi.sharky777.xyz/api/member",
        "domain": "https://www.ab8945621.com", # Used for registration payload and Referer
        "referral_code": "",
        "registration_needs_captcha": False, # Does NOT need captcha for registration
        "origin": "https://www.ab8945621.com", # Used for Origin header
        "active": True
    },
    # --- Example of a disabled API ---
    # {
    #     "name": "DisabledAPI",
    #     "base_url": "https://api.disabled.com/v1/member",
    #     "domain": "https://www.disabled.com",
    #     "referral_code": "off",
    #     "registration_needs_captcha": False,
    #     "origin": "https://www.disabled.com",
    #     "active": False # This API will be skipped
    # },
]


# --- Helper Functions (Unchanged) ---
def generate_random_membercode():
    letters = string.ascii_letters
    digits = string.digits
    return ''.join(random.choice(letters) for _ in range(5)) + ''.join(random.choice(digits) for _ in range(4))

def generate_password():
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(random.randint(8, 12)))

def generate_fingerprint():
    return ''.join(random.choice('0123456789abcdef') for _ in range(32))

# --- Parameterized API Functions ---

# get_captcha: Unchanged
async def get_captcha(session: aiohttp.ClientSession, base_url: str, api_name: str, headers: dict):
    """API 1: Generate OTP captcha (async), parameterized, uses passed headers"""
    captcha_id = str(uuid4())
    captcha_code = ''.join(random.choice('0123456789') for _ in range(4))
    url = f'{base_url}/requestCaptchaCode'
    params = {'captcha_id': captcha_id, 'captcha_code': captcha_code}

    print(f"DEBUG [{api_name}]: Requesting Captcha - URL: {url}, Params: {params}")
    # print(f"DEBUG [{api_name}]: Captcha GET Headers: {headers}") # Optional: Log headers

    try:
        async with session.get(url, params=params, headers=headers, timeout=15) as response:
            response_body_bytes = await response.read()
            response_encoding = response.get_encoding()
            print(f"DEBUG [{api_name}]: Captcha Response - Status: {response.status}, Encoding: {response_encoding}, Bytes: {len(response_body_bytes)}")
            response_text = ""
            decoded_successfully = False
            if response_body_bytes:
                try:
                    response_text = response_body_bytes.decode(response_encoding)
                    decoded_successfully = True
                except UnicodeDecodeError as ude:
                    print(f"WARN [{api_name}]: Captcha decode failed ('{response_encoding}'): {ude}. Trying latin-1.")
                    try: response_text = response_body_bytes.decode('latin-1'); decoded_successfully = True
                    except Exception as e: print(f"ERROR [{api_name}]: Captcha latin-1 decode failed: {e}")
                except Exception as e: print(f"ERROR [{api_name}]: Captcha body decode error: {e}")

            if response.status == 200:
                 if not response_text.strip():
                      print(f"DEBUG [{api_name}]: Captcha 200 OK with empty/failed decode. Assuming success.")
                      return captcha_id, captcha_code
                 try:
                     data = json.loads(response_text)
                     if data.get('success', False) or data.get('data', False):
                          print(f"DEBUG [{api_name}]: Captcha API returned success JSON.")
                          return captcha_id, captcha_code
                     raise Exception(f"Captcha API failed (JSON): {data.get('error', 'Unknown')}")
                 except json.JSONDecodeError:
                      print(f"DEBUG [{api_name}]: Captcha 200 OK with non-JSON body. Assuming success.")
                      return captcha_id, captcha_code
            raise Exception(f"Captcha API request failed. Status: {response.status}, Body: {response_text[:200]}")
    except Exception as e: raise Exception(f"[{api_name}] Captcha request error: {e}")


# request_otp: Unchanged
async def request_otp(session: aiohttp.ClientSession, base_url: str, api_name: str, headers: dict, mobile: str, prefix: str, captcha_id: str, captcha_code: str, attempt=1):
    """API 2: Request OTP (async), parameterized, uses passed headers"""
    url = f'{base_url}/reqFgtPsw'
    payload = {"mobile": mobile, "prefix": prefix, "captcha_id": captcha_id, "captcha_code": captcha_code}

    print(f"DEBUG [{api_name}]: Attempt {attempt} - OTP Request Payload: mobile={mobile}, captcha_id={captcha_id}")
    # print(f"DEBUG [{api_name}]: OTP POST Headers: {headers}") # Optional: Log headers

    try:
        async with session.post(url, headers=headers, json=payload, timeout=15) as response:
            response_body_bytes = await response.read()
            response_encoding = response.get_encoding()
            print(f"DEBUG [{api_name}]: OTP Response - Status: {response.status}, Encoding: {response_encoding}, Bytes: {len(response_body_bytes)}")
            response_text = ""
            if response_body_bytes:
                try: response_text = response_body_bytes.decode(response_encoding)
                except UnicodeDecodeError as ude:
                    print(f"WARN [{api_name}]: OTP decode failed ('{response_encoding}'): {ude}. Trying latin-1.")
                    try: response_text = response_body_bytes.decode('latin-1')
                    except Exception as e: print(f"ERROR [{api_name}]: OTP latin-1 decode failed: {e}"); response_text = ""
                except Exception as e: print(f"ERROR [{api_name}]: OTP body decode error: {e}"); response_text = ""

            if not response_text.strip():
                 if response.status == 200:
                      print(f"WARN [{api_name}]: OTP 200 OK with empty/failed decode. Assuming SUCCESS based on status (like captcha/reg).")
                      return True, None
                 else: raise Exception(f"OTP status {response.status} with empty/failed decode body.")

            try:
                data = json.loads(response_text)
                if response.status == 200:
                    is_success = data.get('success', None)
                    if is_success is True: print(f"DEBUG [{api_name}]: OTP request successful (success=true)."); return True, None
                    elif is_success is False:
                         err = data.get('error', 'Unknown (success=false)')
                         print(f"DEBUG [{api_name}]: OTP failed via JSON: {err}")
                         return False, ("Phone number not found" if err == 'Phone number not found' else err)
                    else: print(f"WARN [{api_name}]: OTP 200 OK, JSON valid, missing 'success'. Assuming success."); return True, None
                elif response.status == 500:
                    err = data.get('error', 'Unknown 500 error')
                    print(f"DEBUG [{api_name}]: OTP failed 500: {err}")
                    if 'Too Frequent' in err and attempt <= 3:
                         wait = attempt * 5; print(f"Rate limit (500). Wait {wait}s..."); await asyncio.sleep(wait)
                         return await request_otp(session, base_url, api_name, headers, mobile, prefix, captcha_id, captcha_code, attempt + 1)
                    return False, ("Phone number not found" if err == 'Phone number not found' else f"Server error 500: {err}")
                elif response.status == 400:
                    err = data.get('error', 'Unknown 400 error'); code = data.get('code')
                    print(f"DEBUG [{api_name}]: OTP failed 400: Code={code}, Error={err}")
                    if code == '3.692' and attempt <= 3: # Rate limit code observed previously
                        wait = attempt * 5; print(f"Rate limit (400). Wait {wait}s..."); await asyncio.sleep(wait)
                        return await request_otp(session, base_url, api_name, headers, mobile, prefix, captcha_id, captcha_code, attempt + 1)
                    elif 'Captcha error' in err or 'Captcha invalid' in err:
                        return False, "Captcha error/invalid"
                    return False, f"Bad request 400: {err}" # Generic 400 error
                else: raise Exception(f"OTP unexpected status {response.status} with JSON: {data}")

            except json.JSONDecodeError:
                 if response.status == 200:
                     print(f"WARN [{api_name}]: OTP 200 OK but with invalid JSON body. Assuming SUCCESS based on status. Body: {response_text[:100]}")
                     return True, None
                 else: raise Exception(f"Invalid JSON response from OTP server (Status {response.status}): {response_text[:100]}")

    except Exception as e: raise Exception(f"[{api_name}] OTP request error (Attempt {attempt}): {e}")


# register_user: MODIFIED to add Referer for Krikya
async def register_user(session: aiohttp.ClientSession, api_config: dict, headers: dict, mobile: str, get_headers_for_captcha: dict):
    """API 3: Register user (async), parameterized, uses passed headers"""
    api_name = api_config["name"]
    base_url = api_config["base_url"]
    domain = api_config["domain"] # Used for payload domain field and potentially Referer
    referral_code = api_config["referral_code"]
    needs_captcha = api_config["registration_needs_captcha"]

    url = f'{base_url}'

    reg_captcha_id = None
    reg_captcha_code = None
    # --- Captcha Handling for Registration ---
    if needs_captcha:
        print(f"DEBUG [{api_name}]: Registration requires captcha. Requesting...")
        try:
            reg_captcha_id, reg_captcha_code = await get_captcha(session, base_url, api_name + "-RegCaptcha", get_headers_for_captcha)
            print(f"DEBUG [{api_name}]: Got registration captcha - ID: {reg_captcha_id}, Code: {reg_captcha_code}")
        except Exception as e:
            print(f"ERROR [{api_name}]: Failed to get captcha specifically for registration: {e}")
            return False, "Failed to get required registration captcha"
    else:
        print(f"DEBUG [{api_name}]: Registration does not require captcha.")
    # --- End Captcha Handling ---

    membercode = generate_random_membercode()
    # --- Base Payload Construction ---
    payload = {
        "membercode": membercode, "password": generate_password(), "currency": "BDT",
        "email": "", "registration_site": "mobile", "mobile": mobile, "line": "",
        "referral_code": referral_code, "is_early_bird": "0", "domain": domain,
        "reg_type": 2, "agent_team": "", "utm_source": None, "utm_medium": None,
        "utm_campaign": None, "s2": None, "fp": generate_fingerprint(), "c_id": None,
        "pid": None, "stag": None, "tracking_url": None
    }
    # --- End Base Payload ---

    # --- API-Specific Payload Adjustments ---
    if needs_captcha and reg_captcha_id and reg_captcha_code:
        payload["captcha_id"] = reg_captcha_id
        payload["captcha_code"] = reg_captcha_code
        print(f"DEBUG [{api_name}]: Added captcha fields to registration payload.")
        if api_name in ["Babu", "Star", "Jaya"]:
             payload["name"] = ""
             print(f"DEBUG [{api_name}]: Added empty 'name' field for captcha registration.")

    if api_name in ["Jaya", "Khela", "Krikya"]:
        payload["verification_code"] = ""
        print(f"DEBUG [{api_name}]: Added empty 'verification_code' field.")

    if api_name == "Khela":
        payload["language"] = "en"
    else:
        payload["language"] = "bd"
    # --- End API-Specific Adjustments ---

    print(f"DEBUG [{api_name}]: Registration Payload: membercode={membercode}, mobile={mobile}, needs_captcha={needs_captcha}, lang={payload.get('language')}")

    # --- Prepare Headers Specific for this Request ---
    # Start with a copy of the headers passed in (which include Origin)
    reg_headers = headers.copy()

    # Add Referer *only* for Krikya registration
    if api_name == "Krikya":
        # Use the 'domain' from config, ensuring it has a trailing slash as per your example
        referer_url = domain
        if not referer_url.endswith('/'):
             referer_url += '/'
        reg_headers['Referer'] = referer_url
        print(f"DEBUG [{api_name}]: Added 'Referer: {referer_url}' header for registration.")
    # else: # Optional: Log if Referer is NOT added
    #    print(f"DEBUG [{api_name}]: 'Referer' header not added for this API.")

    # print(f"DEBUG [{api_name}]: Final Registration POST Headers: {reg_headers}") # Uncomment for full header debug

    # --- Make the POST Request ---
    try:
        # Use the potentially modified reg_headers
        async with session.post(url, headers=reg_headers, json=payload, timeout=20) as response:
            response_body_bytes = await response.read()
            response_encoding = response.get_encoding()
            print(f"DEBUG [{api_name}]: Registration Response - Status: {response.status}, Encoding: {response_encoding}, Bytes: {len(response_body_bytes)}")
            response_text = ""
            if response_body_bytes:
                try: response_text = response_body_bytes.decode(response_encoding)
                except UnicodeDecodeError as ude:
                    print(f"WARN [{api_name}]: Reg decode failed ('{response_encoding}'): {ude}. Trying latin-1.")
                    try: response_text = response_body_bytes.decode('latin-1')
                    except Exception as e: print(f"ERROR [{api_name}]: Reg latin-1 decode failed: {e}"); response_text = ""
                except Exception as e: print(f"ERROR [{api_name}]: Reg body decode error: {e}"); response_text = ""

            # --- Process Response --- (Error handling logic remains the same)
            if response.status == 200:
                if not response_text.strip():
                    print(f"DEBUG [{api_name}]: Reg 200 OK with empty/failed decode. Assuming SUCCESS.")
                    return True, None
                try:
                    data = json.loads(response_text)
                    is_success_flag = data.get('success')
                    if is_success_flag is False:
                        err = data.get('error', 'Unknown (success=false)')
                        print(f"DEBUG [{api_name}]: Reg failed (JSON success=false): {err}")
                        if 'Mobile number already exists' in err or 'Mobile number already registered' in err: return False, "Mobile number already registered"
                        elif 'Captcha error' in err or 'Captcha invalid' in err: return False, "Captcha error/invalid"
                        else: return False, err
                    else:
                        print(f"DEBUG [{api_name}]: Registration successful (parsed JSON, success!=false).")
                        return True, None
                except json.JSONDecodeError:
                     print(f"WARN [{api_name}]: Reg 200 OK with invalid JSON body. Assuming SUCCESS based on status.")
                     return True, None
            elif response.status == 400:
                 try:
                     data = json.loads(response_text)
                     err = data.get('error', 'Unknown 400 error'); code = data.get('code')
                     print(f"DEBUG [{api_name}]: Reg failed 400: Code={code}, Error={err}")
                     if 'Mobile number already exists' in err or 'Mobile number already registered' in err: return False, "Mobile number already registered"
                     elif 'Captcha error' in err or 'Captcha invalid' in err: return False, "Captcha error/invalid"
                     else: return False, f"Reg failed 400: {err}"
                 except json.JSONDecodeError: raise Exception(f"Reg 400 but invalid JSON: {response_text[:100]}")
            else: raise Exception(f"Reg failed status {response.status}: {response_text[:100]}")
            # --- End Process Response ---

    except Exception as e: raise Exception(f"[{api_name}] Registration request error: {e}")


# --- Workflow Functions (Unchanged) ---

async def run_single_api_process(session: aiohttp.ClientSession, api_config: dict, mobile: str, prefix: str, debug: bool):
    """Runs the 3-step (+ retry) process for a single configured API."""
    api_name = api_config["name"]
    base_url = api_config["base_url"]
    origin = api_config.get("origin")
    # Determine if registration requires captcha *for this specific API*
    # This is needed because registration function might be called conditionally
    registration_needs_captcha = api_config.get("registration_needs_captcha", False)


    print(f"\n🚀 === Processing API: {api_name} ({base_url}) ===")

    # --- Prepare Headers ---
    # Start with copies of the base headers defined globally
    # These headers will be passed to get_captcha, request_otp, and register_user
    # register_user up make its own copy and add Re
