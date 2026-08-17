"""Gerenciador de sessão do navegador (Chrome) com perfil persistente e stealth.

Objetivo: reduzir a frequência de reCAPTCHA reutilizando cookies/sessão entre
execuções (user-data-dir persistente) e aplicando técnicas anti-detecção
(navigator.webdriver=false, excludeSwitches, etc).

Este módulo é propositalmente independente de Flet para poder ser reutilizado
tanto na aplicação desktop quanto no futuro backend web.
"""
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Caminhos do Chrome no Windows (tenta vários candidatos)
_CHROME_BIN_CANDIDATES = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
]


def resolve_browser_binary() -> str | None:
    """Retorna o caminho do executável do Chrome/Edge instalado."""
    for candidate in _CHROME_BIN_CANDIDATES:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def default_profile_dir() -> str:
    """Diretório do perfil persistente do navegador da aplicação."""
    return os.path.join(os.path.expanduser('~'), '.ponto_sms_flet', 'chrome_profile')


def build_chrome_options(
        profile_dir: str,
        headless: bool = False,
        print_to_pdf: bool = False,
        window_size: tuple[int, int] = (1280, 900),
        start_minimized: bool = False,
) -> Options:
    """Monta as opções do Chrome com foco em estabilidade e anti-detecção."""
    options = Options()

    # Perfil persistente (reuso de cookies/sessão de login)
    options.add_argument(f'--user-data-dir={profile_dir}')

    # Abre a janela já minimizada (janela do backend fica em segundo plano;
    # só é maximizada quando um novo login/captcha é necessário)
    if start_minimized:
        options.add_argument('--start-minimized')

    # Estabilidade básica
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-notifications')
    options.add_argument('--lang=pt-BR')
    options.add_argument(f'--window-size={window_size[0]},{window_size[1]}')

    # Mantém o comportamento de impressão usado pelo pipeline de PDF
    if print_to_pdf:
        options.add_argument('--print-to-pdf')

    if headless:
        options.add_argument('--headless=new')
        # Em modo headless o user-agent/disable-blink ajudam na persistência
        options.add_argument('--disable-blink-features=AutomationControlled')
        # Em convenção de acordo com o reCAPTCHA: manter janela padrão
        options.add_argument('--window-size=1920,1080')

    # Reduz a marcação de automação no navegador
    options.add_experimental_option('excludeSwitches', [
        'enable-automation',
        'enable-blink-features=AutomationControlled',
    ])
    options.add_experimental_option('useAutomationExtension', False)

    # User-Agent realista (Chrome 125 no Windows 10)
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    )

    # Desativa features de automação do Blink
    options.add_argument('--disable-blink-features=AutomationControlled')

    # Desativa gerenciador de senha e prompts que atrapalham a sessão
    prefs = {
        'credentials_enable_service': False,
        'profile.password_manager_enabled': False,
        'profile.default_content_setting_values.notifications': 2,
    }
    options.add_experimental_option('prefs', prefs)

    binary = resolve_browser_binary()
    if binary:
        options.binary_location = binary

    return options


def _apply_stealth(driver) -> None:
    """Aplica técnicas anti-detecção no navigator/webdriver da sessão.

    Usa selenium-stealth quando disponível; caso contrário, injeta o
    mínimo via CDP antes de qualquer navegação.
    """
    try:
        from selenium_stealth import stealth

        stealth(
            driver,
            languages=['pt-BR', 'pt-BR', 'pt'],
            vendor='Google Inc.',
            platform='Win32',
            webgl_vendor='Intel Inc.',
            renderer='Intel Iris OpenGL Engine',
            fix_hairline=True,
            run_on_insecure_origins=True,
        )
        return
    except Exception:
        pass

    # Fallback manual via CDP (executa antes de cada navegação)
    driver.execute_cdp_cmd(
        'Page.addScriptToEvaluateOnNewDocument',
        {
            'source':
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        },
    )


def _apply_advanced_stealth(driver) -> None:
    """Técnicas avançadas de anti-detecção via CDP.

    Patches o navigator, chrome.runtime e permissions para parecer um
    navegador real (não automatizado). Reduz a quantidade de rodadas
    do reCAPTCHA v2.
    """
    stealth_js = r"""
    // --- navigator.webdriver ---
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    delete navigator.__proto__.webdriver;

    // --- navigator.plugins (simula plugins reais do Chrome) ---
    Object.defineProperty(navigator, 'plugins', {
      get: () => {
        const plugins = [
          {name: 'Chrome PDF Plugin', description: 'Portable Document Format',
           filename: 'internal-pdf-viewer', length: 1,
           item: (i) => ({name: 'Chrome PDF Plugin'})},
          {name: 'Chrome PDF Viewer', description: '',
           filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', length: 1,
           item: (i) => ({name: 'Chrome PDF Viewer'})},
          {name: 'Native Client', description: '',
           filename: 'internal-nacl-plugin', length: 2,
           item: (i) => ({name: 'Native Client'})},
        ];
        plugins.item = (i) => plugins[i] || null;
        plugins.namedItem = (name) => plugins.find(p => p.name === name) || null;
        plugins.refresh = () => {};
        return plugins;
      }
    });

    // --- navigator.languages ---
    Object.defineProperty(navigator, 'languages', {
      get: () => ['pt-BR', 'pt', 'en-US', 'en']
    });

    // --- navigator.language (singular) ---
    Object.defineProperty(navigator, 'language', {
      get: () => 'pt-BR'
    });

    // --- navigator.hardwareConcurrency (CPU cores realistas) ---
    Object.defineProperty(navigator, 'hardwareConcurrency', {
      get: () => 8
    });

    // --- navigator.deviceMemory (RAM realista) ---
    Object.defineProperty(navigator, 'deviceMemory', {
      get: () => 8
    });

    // --- chrome.runtime (finge que extensão está instalada) ---
    window.chrome = window.chrome || {};
    window.chrome.runtime = window.chrome.runtime || {
      PlatformOs: {MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd'},
      PlatformArch: {ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64', MIPS: 'mips', MIPS64: 'mips64'},
      PlatformNaclArch: {ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64', MIPS: 'mips', MIPS64: 'mips64'},
      RequestUpdateCheckStatus: {THROTTLED: 'throttled', NO_UPDATE: 'no_update', UPDATE_AVAILABLE: 'update_available'},
      OnInstalledReason: {INSTALL: 'install', UPDATE: 'update', CHROME_UPDATE: 'chrome_update', SHARED_MODULE_UPDATE: 'shared_module_update'},
      OnRestartRequiredReason: {APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic'},
      connect: () => {},
      sendMessage: () => {},
    };

    // --- Permissões (notifications) ---
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
      parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
    );

    // --- WebGL Vendor/Renderer realistas ---
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
      if (parameter === 37445) return 'Intel Inc.';
      if (parameter === 37446) return 'Intel Iris OpenGL Engine';
      return getParameter.call(this, parameter);
    };
    """
    driver.execute_cdp_cmd(
        'Page.addScriptToEvaluateOnNewDocument',
        {'source': stealth_js}
    )
    logger.debug('Stealth avançado aplicado (CDP).')


def create_driver(
        profile_dir: str | None = None,
        headless: bool = False,
        print_to_pdf: bool = False,
        apply_stealth: bool = True,
        maximize_window: bool = True,
        start_minimized: bool = False,
):
    """Cria e retorna uma instância do WebDriver do Chrome.

    Tenta usar `undetected_chromedriver` (mais resistente a detecção) e, se
    indisponível, cai para o selenium.webdriver padrão com stealth.
    """
    profile_dir = profile_dir or default_profile_dir()
    os.makedirs(profile_dir, exist_ok=True)

    options = build_chrome_options(
        profile_dir=profile_dir,
        headless=headless,
        print_to_pdf=print_to_pdf,
        start_minimized=start_minimized,
    )

    # 1ª tentativa: selenium padrão + stealth (estável e suficiente)
    try:
        driver = webdriver.Chrome(options=options)
        if apply_stealth:
            _apply_stealth(driver)
            _apply_advanced_stealth(driver)
        if maximize_window:
            driver.maximize_window()
        return driver
    except Exception:
        pass

    # 2ª tentativa: undetected_chromedriver (gerencia o perfil internamente)
    try:
        import undetected_chromedriver as uc

        driver = uc.Chrome(user_data_dir=profile_dir, headless=headless)
        if maximize_window:
            driver.maximize_window()
        return driver
    except Exception:
        pass

    # 3ª tentativa: selenium padrão sem stealth
    driver = webdriver.Chrome()
    if maximize_window:
        driver.maximize_window()
    return driver
