"""Gerenciador de sessão do navegador (Chrome) com perfil persistente e stealth.

Objetivo: reduzir a frequência de reCAPTCHA reutilizando cookies/sessão entre
execuções (user-data-dir persistente) e aplicando técnicas anti-detecção
(navigator.webdriver=false, excludeSwitches, etc).

Este módulo é propositalmente independente de Flet para poder ser reutilizado
tanto na aplicação desktop quanto no futuro backend web.
"""
import logging
import os
import shutil
import subprocess
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)

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
    _home = os.path.expanduser('~')
    _path = os.path.join(_home, '.ponto_sms_flet', 'chrome_profile')
    logger.info('DIAG default_profile_dir: expanduser(~)=%s -> %s', _home, _path)
    return _path


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

    # Força o ChromeDriver a usar PORTA (não pipe) para o DevTools.
    # ChromeDriver recente (>=138) usa --remote-debugging-pipe por padrão,
    # que em alguns Windows faz o Chrome encerrar em ~0,1s com
    # "session not created: Chrome instance exited" (verificado na VM).
    # Com --remote-debugging-port=0 o próprio sistema escolhe a porta livre.
    options.add_argument('--remote-debugging-port=0')

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

    # Anti-detecção: remove 'enable-automation' do excludeSwitches.
    # O flag --enable-automation é NECESSÁRO para que o Chrome sobreviva
    # em ambientes corporativos com Windows Defender (MsMpEng); sem ele,
    # o processo Chrome é encerrado imediatamente ao iniciar.
    # O navigator.webdriver é ocultado via CDP em _apply_stealth() e
    # _apply_advanced_stealth() para manter a anti-detecção.
    options.add_experimental_option('excludeSwitches', [
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


def _edge_binary() -> str | None:
    """Retorna o caminho do Edge se instalado (fallback ao Chrome)."""
    candidates = [
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _build_edge_options(
        profile_dir: str,
        headless: bool = False,
        window_size: tuple[int, int] = (1280, 900),
) -> 'Options':
    """Opções do Edge (mesmas bases de estabilidade/anti-detecção do Chrome)."""
    from selenium.webdriver.edge.options import Options as EdgeOptions

    options = EdgeOptions()
    options.add_argument(f'--user-data-dir={profile_dir}')
    options.add_argument('--remote-debugging-port=0')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-notifications')
    options.add_argument('--lang=pt-BR')
    options.add_argument(f'--window-size={window_size[0]},{window_size[1]}')
    if headless:
        options.add_argument('--headless=new')
    options.add_experimental_option('excludeSwitches', [
        'enable-blink-features=AutomationControlled',
    ])
    options.add_experimental_option('useAutomationExtension', False)
    edge = _edge_binary()
    if edge:
        options.binary_location = edge
    return options


def default_edge_profile_dir() -> str:
    """Perfil separado para o Edge (fallback), isolado do lock do Chrome.

    O Chromium sinaliza singleton pela PASTA do user-data-dir; compartilhar
    o chrome_profile com o Edge faz o Edge "delegar" e sair imediatamente
    ("Chrome instance exited") quando o Chrome ainda segura o perfil.
    """
    return os.path.join(os.path.dirname(default_profile_dir()), 'edge_profile')


def cleanup_orphan_browsers(profile_dir: str | None = None) -> None:
    """Encerra Chrome/Edge órfãos presos ao perfil persistente (Windows).

    O Chrome trava o 'user-data-dir' enquanto está aberto. Se uma instância
    anterior (crashada/órfã) ainda estiver usando o mesmo perfil, uma nova
    chamada a `webdriver.Chrome` falha com "Chrome instance exited".

    Aqui matamos apenas processos (chrome.exe/msedge.exe) cuja linha de comando
    referencia o perfil desta aplicação -- o browser do usuário fica intocado.

    Estratégia em duas etapas:
      1) taskkill /PID para cada processo encontrado pelo PowerShell;
      2) Se taskkill falhar (permissão, processo em outra sessão), usa
         ctypes.TerminateProcess como fallback direto via Windows API.
    """
    profile_dir = profile_dir or default_profile_dir()
    if os.name != 'nt':
        return
    try:
        profile_norm = os.path.normcase(profile_dir).lower()
        ps = subprocess.run(
            [
                'powershell', '-NoProfile', '-Command',
                "Get-CimInstance Win32_Process | "
                "Where-Object { $_.Name -eq 'chrome.exe' -or "
                "$_.Name -eq 'msedge.exe' } | "
                "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress",
            ],
            capture_output=True, text=True, timeout=30, errors='replace',
        )
        if ps.returncode != 0:
            logger.debug('cleanup_orphan_browsers: powershell retornou %s.', ps.returncode)
            return

        import json
        data = json.loads(ps.stdout or '[]')
        if isinstance(data, dict):
            data = [data]
        killed = 0
        for proc in data:
            cmd = (proc.get('CommandLine') or '') + ''
            if profile_norm in os.path.normcase(cmd).lower():
                pid = proc.get('ProcessId')
                try:
                    pid = int(pid)
                except (TypeError, ValueError):
                    continue
                # Tentativa 1: taskkill
                result = subprocess.run(
                    ['taskkill', '/PID', str(pid), '/F'],
                    capture_output=True, text=True, timeout=15,
                )
                if result.returncode == 0:
                    killed += 1
                    continue
                # Tentativa 2: Windows API direta (fallback)
                try:
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    PROCESS_TERMINATE = 0x0001
                    handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
                    if handle:
                        kernel32.TerminateProcess(handle, 1)
                        kernel32.CloseHandle(handle)
                        killed += 1
                        logger.warning(
                            'Orfao PID %s morto via Windows API (taskkill falhou).', pid)
                except Exception:
                    pass
        if killed:
            logger.warning(
                'cleanup_orphan_browsers: %d processo(s) encerrado(s) do perfil %s.',
                killed, profile_dir)
    except Exception:
        logger.debug('cleanup_orphan_browsers falhou.', exc_info=True)


def create_driver(
        profile_dir: str | None = None,
        headless: bool = False,
        print_to_pdf: bool = False,
        apply_stealth: bool = True,
        maximize_window: bool = True,
        start_minimized: bool = False,
):
    """Cria e retorna uma instância do WebDriver do Chrome (ou Edge).

    Tenta, em ordem:
      1) Chrome com o perfil persistente da aplicação (reuso de cookies);
      2) Chrome com o perfil persistente RECRIADO do zero (contorna
         lock/corrupção do perfil - causa do "Chrome instance exited");
      3) Edge (msedge.exe) com PERFIL PRÓPRIO isolado - fallback final.
    """
    profile_dir = profile_dir or default_profile_dir()
    os.makedirs(profile_dir, exist_ok=True)

    # Diagnóstico: verifica se há navegador disponível
    binary = resolve_browser_binary()
    if binary:
        logger.info('Navegador detectado: %s', binary)
    else:
        logger.warning(
            'Nenhum navegador (Chrome/Edge) encontrado nos caminhos padrão. '
            'O Selenium tentará usar o ChromeDriver padrão.')

    # Limpa instâncias órfãs (Chrome/Edge) que estejam segurando o lock do
    # perfil; caso contrário uma nova sessão falha com "session not created:
    # Chrome instance exited".
    cleanup_orphan_browsers(profile_dir)

    def _launch(options, label: str):
        """Tenta criar o driver com as opções dadas; retorna driver ou None."""
        drv = None
        try:
            drv = webdriver.Chrome(options=options)
            if apply_stealth:
                _apply_stealth(drv)
                _apply_advanced_stealth(drv)
            if maximize_window:
                drv.maximize_window()
            return drv
        except Exception as e:
            if drv is not None:
                try:
                    drv.quit()
                except Exception:
                    pass
            logger.warning('create_driver: %s falhou (%s: %s).', label, type(e).__name__, e)
            return None

# 1ª tentativa: perfil persistente da aplicação (reuso de sessão/cookies)
    options = build_chrome_options(
        profile_dir=profile_dir,
        headless=headless,
        print_to_pdf=print_to_pdf,
        start_minimized=start_minimized,
    )
    driver = _launch(options, 'tentativa 1 (perfil persistente)')
    if driver is not None:
        return driver

    # 2ª tentativa: PERFIL PERSISTENTE RECRIADO DO ZERO. Descarta o diretório
    # corrompido/travado (causa do "Chrome instance exited") e recria a
    # estrutura vazia, mantendo o caminho default (persistência de cookies).
    # Se o processo órfão recusar morrer (ex.: WinError 5), a remoção é
    # tentada em loop até os handles serem liberados; se ainda assim falhar,
    # seguimos para o Edge (que usa um perfil isolado).
    try:
        for attempt in range(2):
            if os.path.isdir(profile_dir):
                cleanup_orphan_browsers(profile_dir)
                time.sleep(1.0)
                try:
                    shutil.rmtree(profile_dir, ignore_errors=False)
                    break
                except PermissionError:
                    if attempt == 1:
                        raise
                    logger.warning(
                        'create_driver: perfil ainda travado, matando órfãos '
                        'e tentando de novo (tentativa %d).', attempt + 2)
                    cleanup_orphan_browsers(profile_dir)
                    time.sleep(1.5)
            else:
                break
        os.makedirs(profile_dir, exist_ok=True)
        logger.warning(
            'create_driver: perfil persistente recriado do zero (%s).', profile_dir)
        options_reset = build_chrome_options(
            profile_dir=profile_dir,
            headless=headless,
            print_to_pdf=print_to_pdf,
            start_minimized=start_minimized,
        )
        driver = _launch(options_reset, 'tentativa 2 (perfil recriado do zero)')
        if driver is not None:
            return driver
    except Exception as e:
        logger.warning('create_driver: tentativa 2 (reset do perfil) falhou (%s).', e)

    # 3ª tentativa: Edge como fallback (Windows tem Edge sempre).
    # Usa um PERFIL ISOLADO (edge_profile): o Chromium sinaliza singleton
    # pela pasta; compartilhar chrome_profile faria o Edge "delegar" ao
    # Chrome e sair na hora (mesmo "Chrome instance exited").
    if _edge_binary():
        edge_profile = default_edge_profile_dir()
        try:
            if os.path.isdir(edge_profile):
                cleanup_orphan_browsers(edge_profile)
                time.sleep(1.0)
                try:
                    shutil.rmtree(edge_profile, ignore_errors=False)
                except PermissionError:
                    logger.warning(
                        'create_driver: edge_profile travado, seguindo com ele '
                        'mesmo assim (remocao falhou).')
            os.makedirs(edge_profile, exist_ok=True)
        except Exception as e:
            logger.warning('create_driver: preparo do edge_profile falhou (%s).', e)

        edge_options = _build_edge_options(
            profile_dir=edge_profile, headless=headless,
        )
        try:
            from selenium.webdriver.edge.webdriver import WebDriver as EdgeDriver
            driver = EdgeDriver(options=edge_options)
            if apply_stealth:
                _apply_stealth(driver)
                _apply_advanced_stealth(driver)
            if maximize_window:
                driver.maximize_window()
            return driver
        except Exception as e:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            logger.warning('create_driver: tentativa 3 (Edge) falhou (%s).', e)

    # 4ª tentativa (fallback geral): selenium padrão sem stealth
    options = build_chrome_options(
        profile_dir=profile_dir,
        headless=headless,
        print_to_pdf=print_to_pdf,
        start_minimized=start_minimized,
    )
    try:
        driver = webdriver.Chrome(options=options)
        if maximize_window:
            driver.maximize_window()
        return driver
    except Exception as e:
        binary_info = f' (navegador: {binary})' if binary else ''
        raise RuntimeError(
            f'Não foi possível iniciar o navegador{binary_info}. '
            f'Verifique se Chrome/Edge está instalado e se o Windows Defender '
            f'não está bloqueando o processo.'
        ) from e
