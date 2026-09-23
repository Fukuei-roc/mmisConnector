from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
import urllib3
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


PAGE_SEQ_RE = re.compile(r'var\s+PAGESEQNUM\s*=\s*"(?P<value>\d+)"')
UI_SESSION_RE = re.compile(
    r'var\s+UISESSIONID\s*=\s*decodeURIComponent\("(?P<value>\d+)"\)'
)
CSRF_TOKEN_RE = re.compile(r'var\s+CSRFTOKEN\s*=\s*"(?P<value>[^"]+)"')
APP_ID_RE = re.compile(r'var\s+APPID\s*=\s*"(?P<value>[^"]+)"')
REDIRECT_SESSION_RE = re.compile(r"[?&]uisessionid=(?P<value>\d+)")
LOGIN_SIGNAL = "loginform"


class MMISClientError(RuntimeError):
    """A safe, user-facing MMIS client error."""


@dataclass(frozen=True)
class MMISConfig:
    username: str
    password: str
    base_url: str = "https://ap.nmmis.railway.gov.tw"
    verify_ssl: bool = True
    timeout_seconds: float = 20.0

    @classmethod
    def from_env(cls, dotenv_path: str | None = None) -> "MMISConfig":
        load_dotenv(dotenv_path=dotenv_path)
        username = os.getenv("MMIS_USERNAME", "").strip()
        password = os.getenv("MMIS_PASSWORD", "")
        base_url = os.getenv(
            "MMIS_BASE_URL", "https://ap.nmmis.railway.gov.tw"
        ).rstrip("/")
        verify_ssl = os.getenv("MMIS_VERIFY_SSL", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        try:
            timeout_seconds = float(os.getenv("MMIS_TIMEOUT_SECONDS", "20"))
        except ValueError as exc:
            raise MMISClientError("MMIS_TIMEOUT_SECONDS 必須是數字") from exc

        if not username or not password:
            raise MMISClientError(".env 缺少 MMIS_USERNAME 或 MMIS_PASSWORD")
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise MMISClientError("MMIS_BASE_URL 必須是有效的 HTTPS URL")
        if timeout_seconds <= 0:
            raise MMISClientError("MMIS_TIMEOUT_SECONDS 必須大於 0")
        return cls(username, password, base_url, verify_ssl, timeout_seconds)


@dataclass(frozen=True)
class PageState:
    ui_session_id: str
    page_seq: int
    csrf_token: str
    app_id: str
    page_url: str


def parse_page_state(text: str, page_url: str) -> PageState:
    matches = {
        "page_seq": PAGE_SEQ_RE.search(text),
        "ui_session_id": UI_SESSION_RE.search(text),
        "csrf_token": CSRF_TOKEN_RE.search(text),
        "app_id": APP_ID_RE.search(text),
    }
    missing = [name for name, match in matches.items() if match is None]
    if missing:
        raise MMISClientError(
            "MMIS 頁面缺少必要狀態欄位: " + ", ".join(missing)
        )
    return PageState(
        ui_session_id=matches["ui_session_id"].group("value"),
        page_seq=int(matches["page_seq"].group("value")),
        csrf_token=matches["csrf_token"].group("value"),
        app_id=matches["app_id"].group("value"),
        page_url=page_url,
    )


class MMISSession:
    """Part 1: authenticate and retain one in-memory HTTP session."""

    def __init__(
        self,
        config: MMISConfig,
        session: requests.Session | None = None,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.session.verify = config.verify_ssl
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/147.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            }
        )
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.4,
            status_forcelist=[429, 500, 502, 503, 504],
            # Never automatically replay credential or Maximo event POSTs.
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.state: PageState | None = None
        if not config.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @property
    def login_page_url(self) -> str:
        return f"{self.config.base_url}/maximo/webclient/login/login.jsp?welcome=true"

    @property
    def event_url(self) -> str:
        return f"{self.config.base_url}/maximo/ui/maximo.jsp"

    def request(
        self,
        method: str,
        url: str,
        *,
        expected_status: tuple[int, ...] = (200,),
        **kwargs: object,
    ) -> requests.Response:
        expected_origin = urlparse(self.config.base_url)
        request_origin = urlparse(url)
        if (
            request_origin.scheme.lower() != expected_origin.scheme.lower()
            or request_origin.netloc.lower() != expected_origin.netloc.lower()
        ):
            raise MMISClientError("拒絕非 MMIS 同源的網路請求")
        try:
            response = self.session.request(
                method,
                url,
                timeout=self.config.timeout_seconds,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise MMISClientError(f"MMIS 網路請求失敗: {type(exc).__name__}") from exc
        if response.status_code not in expected_status:
            raise MMISClientError(
                f"MMIS 回傳非預期 HTTP 狀態: {response.status_code}"
            )
        return response

    def login(self) -> PageState:
        login_page = self.request("GET", self.login_page_url)
        soup = BeautifulSoup(login_page.text, "html.parser")
        form = soup.find("form", id="loginform")
        if form is None:
            raise MMISClientError("登入頁找不到 loginform")

        form_data: dict[str, str] = {}
        for element in form.find_all("input"):
            name = element.get("name")
            if name:
                form_data[str(name)] = str(element.get("value", ""))
        form_data["username"] = self.config.username
        form_data["password"] = self.config.password

        action = str(form.get("action") or "/maximo/webclient/login/mxlogin.jsp?welcome=true")
        response = self.request(
            "POST",
            urljoin(self.login_page_url, action),
            data=form_data,
            headers={"Referer": self.login_page_url},
            allow_redirects=False,
            expected_status=(302, 303),
        )
        location = response.headers.get("Location", "")
        session_match = REDIRECT_SESSION_RE.search(location)
        if not session_match:
            raise MMISClientError("登入回應缺少 uisessionid redirect")

        start_url = (
            f"{self.config.base_url}/maximo/ui/login"
            f"?uisessionid={session_match.group('value')}"
            "&event=loadapp&value=startcntr"
        )
        start_response = self.request("GET", start_url)
        if LOGIN_SIGNAL in start_response.text and "使用者登錄" in start_response.text:
            raise MMISClientError("MMIS 登入失敗")
        self.state = parse_page_state(start_response.text, start_response.url)
        return self.state

    def refresh_state(self, page_url: str | None = None) -> tuple[PageState, str]:
        if self.state is None:
            raise MMISClientError("尚未登入 MMIS")
        response = self.request("GET", page_url or self.state.page_url)
        if LOGIN_SIGNAL in response.text and "使用者登錄" in response.text:
            raise MMISClientError("MMIS session 已失效")
        self.state = parse_page_state(response.text, response.url)
        return self.state, response.text
