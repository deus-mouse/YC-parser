from selenium.common.exceptions import TimeoutException

from colorama import Fore


class SeleniumErrorHandler:
    """Сохранение отладочных данных при ошибках Selenium и повторный выброс исключения."""

    def __init__(self, driver, prefix: str = "debug"):
        self.driver = driver
        self.prefix = prefix

    def handle(self, exc: Exception, context: str = "") -> None:
        """
        Сохраняет скриншот и HTML страницы, выводит сообщение, пробрасывает исключение дальше.
        context — имя места ошибки (например "find_masters"), используется в имени файлов и в логе.
        """
        tag = f"{self.prefix}_{context}" if context else self.prefix
        screenshot_path = f"{tag}.png"
        html_path = f"{tag}.html"

        try:
            self.driver.save_screenshot(screenshot_path)
        except Exception:
            pass
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
        except Exception:
            pass

        title = getattr(self.driver, "title", "") or ""
        msg = self._message_for(exc, context, title)
        print(f"{Fore.RED}{msg}")
        print(f"Сохранены {screenshot_path} и {html_path}")
        raise exc

    def _message_for(self, exc: Exception, context: str, title: str) -> str:
        """Текст сообщения в зависимости от типа исключения."""
        if isinstance(exc, TimeoutException):
            return f"Таймаут в {context or 'операции'}. Title страницы: {title}"
        return f"Ошибка в {context or 'операции'}: {exc}. Title: {title}"
