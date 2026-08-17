"""Solução de reCAPTCHA v2 de forma transparente para o usuário final.

Estratégia em camadas:
1. Sessão persistente + stealth (browser_session) evita que o captcha apareça.
2. Se aparecer o checkbox "Não sou um robô", tenta clique e espera passar sem
   desafio (na maioria dos casos com fingerprint limpo ele passa sozinho).
3. Se o clique disparar desafio de imagem, usa uma API paga (2Captcha ou
   CapSolver) configurada via .env (CAPTCHA_API_KEY / CAPTCHA_PROVIDER).
4. Se nada disso funcionar, sinaliza que é necessária intervenção manual.

Configuração opcional no .env:
- CAPTCHA_PROVIDER=2captcha|capsolver   (ativo apenas se CAPTCHA_API_KEY preenchida)
- CAPTCHA_API_KEY=...                   (chave da API)
- CAPTCHA_SITEKEY=...                   (opcional; por padrão é detectada no DOM)
"""
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

# Selectores conhecidos do reCAPTCHA v2 (checkbox e desafio de imagem)
_ANCHOR_IFRAME_XPATH = "//iframe[contains(@src, 'recaptcha/api2/anchor')]"
_BFRAME_IFRAME_XPATH = "//iframe[contains(@src, 'recaptcha/api2/bframe')]"
_RESPONSE_TEXTAREA_ID = 'g-recaptcha-response'


@dataclass
class CaptchaSolveResult:
    """Resultado da tentativa de resolução do reCAPTCHA."""

    success: bool = False
    strategy: str = 'none'  # none | checkbox_click | checkbox_pass | api | manual_required
    reason: str = ''
    token: Optional[str] = None
    sitekey: Optional[str] = None
    diagnostics: dict = field(default_factory=dict)


class CaptchaSolver:
    """Resolve reCAPTCHA v2 presente na página de login do portal."""

    def __init__(self, driver, page_url: str,
                 provider: Optional[str] = None,
                 api_key: Optional[str] = None,
                 api_timeout: int = 180,
                 sitekey: Optional[str] = None):
        self.driver = driver
        self.page_url = page_url
        self.provider = (provider or os.getenv('CAPTCHA_PROVIDER') or '').strip().lower()
        self.api_key = api_key or os.getenv('CAPTCHA_API_KEY') or ''
        self.api_timeout = api_timeout
        self.sitekey = sitekey or os.getenv('CAPTCHA_SITEKEY') or ''
        self.timeout = 10

    # ---------------------------- DETECÇÃO ----------------------------

    def is_present(self) -> bool:
        """Verifica se há iframe de checkbox/ancora do reCAPTCHA na página."""
        try:
            return bool(self.driver.find_elements(By.XPATH, _ANCHOR_IFRAME_XPATH)) or bool(
                self.driver.find_elements(By.ID, _RESPONSE_TEXTAREA_ID))
        except Exception:
            return False

    def detect_sitekey(self) -> Optional[str]:
        """Tenta detectar a sitekey do reCAPTCHA no DOM (data-sitekey)."""
        if self.sitekey:
            return self.sitekey
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, '.g-recaptcha')
            key = element.get_attribute('data-sitekey')
            if key:
                self.sitekey = key
                return key
        except Exception:
            pass
        return None

    def challenge_opened(self) -> bool:
        """Verifica se um desafio de imagem (bframe) foi aberto."""
        try:
            return bool(self.driver.find_elements(By.XPATH, _BFRAME_IFRAME_XPATH))
        except Exception:
            return False

    # ------------------------- CLIQUE NO CHECKBOX ----------------------

    def click_checkbox(self, wait_seconds: int = 6) -> bool:
        """Clica no checkbox e aguarda. True se passou sem desafio de imagem."""
        try:
            # Switch para o iframe do checkbox
            iframe = WebDriverWait(self.driver, self.timeout).until(
                ec.presence_of_element_located((By.XPATH, _ANCHOR_IFRAME_XPATH)))
            self.driver.switch_to.frame(iframe)

            anchor = WebDriverWait(self.driver, self.timeout).until(
                ec.element_to_be_clickable((By.ID, 'recaptcha-anchor')))
            anchor.click()

            # Aguarda o resultado do clique
            WebDriverWait(self.driver, wait_seconds).until(
                ec.element_attribute_to_include((By.ID, 'recaptcha-anchor'), 'aria-checked'))
            checked = anchor.get_attribute('aria-checked')
            self.driver.switch_to.default_content()

            if checked == 'true':
                return True
        except Exception:
            self._safe_back_to_default()
            return False

        self._safe_back_to_default()
        return False

    def _safe_back_to_default(self) -> None:
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass

    # ------------------------- RESOLUÇÃO VIA API -----------------------

    def api_configured(self) -> bool:
        return bool(self.provider and self.api_key)

    def solve_via_api(self) -> Optional[str]:
        """Resolve via API paga e retorna o token g-recaptcha-response."""
        if not self.api_configured():
            return None

        sitekey = self.detect_sitekey()
        if not sitekey:
            raise RuntimeError('Sitekey do reCAPTCHA não encontrada no DOM')

        if self.provider == '2captcha':
            return self._solve_2captcha(sitekey)
        if self.provider == 'capsolver':
            return self._solve_capsolver(sitekey)
        raise ValueError(f'Provedor de captcha não suportado: {self.provider}')

    def _solve_2captcha(self, sitekey: str) -> str:
        import requests

        session = requests.Session()
        create = session.get(
            'https://2captcha.com/in.php',
            params={
                'key': self.api_key,
                'method': 'userrecaptcha',
                'googlekey': sitekey,
                'pageurl': self.page_url,
                'json': 1,
            },
            timeout=30,
        )
        data = create.json()
        if data.get('status') != 1:
            raise RuntimeError(f'2captcha create falhou: {data}')

        task_id = data.get('request')
        deadline = time.time() + self.api_timeout
        while time.time() < deadline:
            time.sleep(5)
            poll = session.get(
                'https://2captcha.com/res.php',
                params={'key': self.api_key, 'action': 'get', 'id': task_id, 'json': 1},
                timeout=30,
            )
            res = poll.json()
            if res.get('status') == 1:
                return res.get('request')
            if res.get('request') not in ('CAPCHA_NOT_READY', 'ERROR_CAPTCHA_UNSOLVABLE'):
                # ainda processando
                continue
        raise RuntimeError('2captcha: tempo esgotado ou captcha impossível')

    def _solve_capsolver(self, sitekey: str) -> str:
        import requests

        session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        create = session.post(
            'https://api.capsolver.com/createTask',
            headers=headers,
            json={
                'clientKey': self.api_key,
                'task': {
                    'type': 'ReCaptchaV2TaskProxyLess',
                    'websiteURL': self.page_url,
                    'websiteKey': sitekey,
                    'isInvisible': False,
                },
            },
            timeout=30,
        )
        task_id = create.json().get('taskId')
        if not task_id:
            raise RuntimeError(f'capsolver create falhou: {create.json()}')

        deadline = time.time() + self.api_timeout
        while time.time() < deadline:
            time.sleep(5)
            poll = session.post(
                'https://api.capsolver.com/getTaskResult',
                headers=headers,
                json={'clientKey': self.api_key, 'taskId': task_id},
                timeout=30,
            )
            res = poll.json()
            status = res.get('status')
            if status == 'ready':
                return res['solution']['gRecaptchaResponse']
            if status == 'failed':
                raise RuntimeError(f'capsolver falhou: {res}')
        raise RuntimeError('capsolver: tempo esgotado')

    # ------------------------- INJEÇÃO DO TOKEN ------------------------

    def inject_token_and_submit(self, token: str, submit_xpath: str) -> bool:
        """Insere o token no textarea e submete o formulário de login."""
        try:
            script = (
                f"var ta=document.getElementById('{_RESPONSE_TEXTAREA_ID}');"
                f"if(ta){{ ta.value=arguments[0]; ta.style.display='block'; }}"
            )
            self.driver.execute_script(script, token)

            # Tenta disparar o callback padrão do site (se existir)
            self.driver.execute_script(
                "if(typeof ___grecaptcha_cfg !== 'undefined'){"
                "try{ window.___grecaptcha_cfg.closed = 1; }catch(e){} }"
            )

            self._safe_back_to_default()
            # Aguarda e clica no botão de login
            button = WebDriverWait(self.driver, self.timeout).until(
                ec.element_to_be_clickable((By.XPATH, submit_xpath)))
            button.click()
            return True
        except Exception:
            self._safe_back_to_default()
            return False

    # ----------------------------- ORQUESTRAÇÃO ------------------------

    def solve(self, submit_xpath: str = "//*[@id='formPonto']/div/div[2]/button",
              password_first_click: bool = True) -> CaptchaSolveResult:
        """Executa a estratégia completa de resolução do captcha.

        password_first_click: caso a página peça "clique aqui" para confirmar
        após o clique no checkbox (fluxo comum), mantém o comportamento.
        """
        result = CaptchaSolveResult()
        result.sitekey = self.detect_sitekey()

        if not self.is_present():
            result.strategy = 'none'
            result.reason = 'reCAPTCHA não detectado na página'
            return result

        # Camada 1+2: clique no checkbox
        passed = self.click_checkbox()
        if passed and not self.challenge_opened():
            result.success = True
            result.strategy = 'checkbox_pass'
            result.reason = 'Checkbox resolvido por clique (sem desafio de imagem)'
            return result

        # Camada 3: API paga
        if self.challenge_opened():
            result.diagnostics['challenge'] = True
            if self.api_configured():
                try:
                    token = self.solve_via_api()
                    if token:
                        if self.inject_token_and_submit(token, submit_xpath):
                            result.success = True
                            result.strategy = 'api'
                            result.token = token
                            result.reason = f'Captcha resolvido via API ({self.provider})'
                            return result
                except Exception as e:
                    result.reason = f'API de captcha falhou: {e}'
            else:
                result.reason = 'Desafio de imagem aberto e nenhuma API configurada'
        else:
            result.reason = 'Checkbox não resolvido automaticamente'

        # Camada 4: requer intervenção manual
        result.success = False
        result.strategy = 'manual_required'
        if not result.reason:
            result.reason = 'Intervenção manual necessária (não resolvido automaticamente)'
        return result
