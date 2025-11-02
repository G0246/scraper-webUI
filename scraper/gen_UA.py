# scraper-webUI
# Dynamic User Agent Generator
# gen_UA.py
# By G0246

from __future__ import annotations

import random
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class BrowserVersion:
    """Holds version information for browsers"""
    major: int
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        if self.patch > 0:
            return f"{self.major}.{self.minor}.{self.patch}"
        elif self.minor > 0:
            return f"{self.major}.{self.minor}"
        return f"{self.major}"

class UserAgentGenerator:
    CHROME_VERSIONS = range(125, 131)  # Chrome 125-130
    FIREFOX_VERSIONS = range(128, 133)  # Firefox 128-132
    SAFARI_VERSIONS = [(16, 5), (16, 6), (17, 0), (17, 1), (17, 2)]  # Safari 16.5-17.2
    EDGE_VERSIONS = range(125, 131)  # Edge 125-130

    # Windows versions
    WINDOWS_VERSIONS = [
        "Windows NT 10.0; Win64; x64",  # Windows 10/11
        "Windows NT 10.0; WOW64",
    ]

    # macOS versions
    MACOS_VERSIONS = [
        "Macintosh; Intel Mac OS X 10_15_7",  # Catalina
        "Macintosh; Intel Mac OS X 11_7_10",  # Big Sur
        "Macintosh; Intel Mac OS X 12_6_8",   # Monterey
        "Macintosh; Intel Mac OS X 13_5",     # Ventura
        "Macintosh; Intel Mac OS X 13_6",
        "Macintosh; Intel Mac OS X 14_0",     # Sonoma
        "Macintosh; Intel Mac OS X 14_1",
    ]

    # Linux distributions
    LINUX_DISTROS = [
        "X11; Linux x86_64",
        "X11; Ubuntu; Linux x86_64",
        "X11; Fedora; Linux x86_64",
    ]

    # Android devices and versions
    ANDROID_DEVICES = [
        ("13", "Pixel 7"),
        ("13", "Pixel 7 Pro"),
        ("14", "Pixel 8"),
        ("14", "Pixel 8 Pro"),
        ("13", "SM-S918B"),  # Samsung Galaxy S23 Ultra
        ("13", "SM-G991B"),  # Samsung Galaxy S21
        ("12", "SM-G998B"),  # Samsung Galaxy S21 Ultra
        ("13", "SM-A536B"),  # Samsung Galaxy A53
        ("14", "SM-S928B"),  # Samsung Galaxy S24 Ultra
    ]

    # iOS versions
    IOS_VERSIONS = [
        "16_5",
        "16_6",
        "17_0",
        "17_1",
        "17_2",
    ]

    # WebKit versions for Safari
    WEBKIT_VERSIONS = [
        "605.1.15",
        "606.1.36",
        "606.2.11",
    ]

    def _random_chrome_version(self) -> str:
        major = random.choice(list(self.CHROME_VERSIONS))
        minor = 0
        patch = random.randint(0, 5000)
        build = random.randint(0, 200)
        return f"{major}.{minor}.{patch}.{build}"

    def _random_firefox_version(self) -> str:
        major = random.choice(list(self.FIREFOX_VERSIONS))
        return f"{major}.0"

    def _random_safari_version(self) -> Tuple[str, str]:
        major, minor = random.choice(self.SAFARI_VERSIONS)
        webkit = random.choice(self.WEBKIT_VERSIONS)
        return f"{major}.{minor}", webkit

    def _generate_chrome_windows(self) -> str:
        version = self._random_chrome_version()
        windows = random.choice(self.WINDOWS_VERSIONS)
        return (
            f"Mozilla/5.0 ({windows}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{version} Safari/537.36"
        )

    def _generate_chrome_macos(self) -> str:
        version = self._random_chrome_version()
        macos = random.choice(self.MACOS_VERSIONS)
        return (
            f"Mozilla/5.0 ({macos}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{version} Safari/537.36"
        )

    def _generate_chrome_linux(self) -> str:
        version = self._random_chrome_version()
        linux = random.choice(self.LINUX_DISTROS)
        return (
            f"Mozilla/5.0 ({linux}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{version} Safari/537.36"
        )

    def _generate_firefox_windows(self) -> str:
        version = self._random_firefox_version()
        windows = random.choice(self.WINDOWS_VERSIONS)
        return (
            f"Mozilla/5.0 ({windows}; rv:{version}) "
            f"Gecko/20100101 Firefox/{version}"
        )

    def _generate_firefox_macos(self) -> str:
        version = self._random_firefox_version()
        macos = random.choice(self.MACOS_VERSIONS)
        return (
            f"Mozilla/5.0 ({macos}; rv:{version}) "
            f"Gecko/20100101 Firefox/{version}"
        )

    def _generate_firefox_linux(self) -> str:
        version = self._random_firefox_version()
        linux = random.choice(self.LINUX_DISTROS)
        return (
            f"Mozilla/5.0 ({linux}; rv:{version}) "
            f"Gecko/20100101 Firefox/{version}"
        )

    def _generate_safari_macos(self) -> str:
        safari_version, webkit = self._random_safari_version()
        macos = random.choice(self.MACOS_VERSIONS)
        return (
            f"Mozilla/5.0 ({macos}) "
            f"AppleWebKit/{webkit} (KHTML, like Gecko) "
            f"Version/{safari_version} Safari/{webkit}"
        )

    def _generate_edge_windows(self) -> str:
        edge_major = random.choice(list(self.EDGE_VERSIONS))
        edge_version = f"{edge_major}.0.{random.randint(2000, 3000)}.{random.randint(0, 100)}"
        chrome_version = self._random_chrome_version()
        windows = random.choice(self.WINDOWS_VERSIONS)
        return (
            f"Mozilla/5.0 ({windows}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{chrome_version} Safari/537.36 Edg/{edge_version}"
        )

    def _generate_chrome_android(self) -> str:
        android_version, device = random.choice(self.ANDROID_DEVICES)
        chrome_version = self._random_chrome_version()
        return (
            f"Mozilla/5.0 (Linux; Android {android_version}; {device}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{chrome_version} Mobile Safari/537.36"
        )

    def _generate_safari_ios(self) -> str:
        ios_version = random.choice(self.IOS_VERSIONS)
        safari_version, webkit = self._random_safari_version()
        return (
            f"Mozilla/5.0 (iPhone; CPU iPhone OS {ios_version} like Mac OS X) "
            f"AppleWebKit/{webkit} (KHTML, like Gecko) "
            f"Version/{safari_version} Mobile/15E148 Safari/604.1"
        )

    def _generate_safari_ipad(self) -> str:
        ios_version = random.choice(self.IOS_VERSIONS)
        safari_version, webkit = self._random_safari_version()
        return (
            f"Mozilla/5.0 (iPad; CPU OS {ios_version} like Mac OS X) "
            f"AppleWebKit/{webkit} (KHTML, like Gecko) "
            f"Version/{safari_version} Mobile/15E148 Safari/604.1"
        )

    def _generate_firefox_android(self) -> str:
        android_version = random.choice([v[0] for v in self.ANDROID_DEVICES])
        firefox_version = self._random_firefox_version()
        return (
            f"Mozilla/5.0 (Android {android_version}; Mobile; rv:{firefox_version}) "
            f"Gecko/{firefox_version} Firefox/{firefox_version}"
        )

    def generate_desktop(self) -> str:
        generators = [
            self._generate_chrome_windows,
            self._generate_chrome_macos,
            self._generate_chrome_linux,
            self._generate_firefox_windows,
            self._generate_firefox_macos,
            self._generate_firefox_linux,
            self._generate_safari_macos,
            self._generate_edge_windows,
        ]
        # Weight Chrome and Firefox more heavily (more common)
        weights = [20, 15, 10, 15, 10, 8, 12, 10]
        chosen_generator = random.choices(generators, weights=weights, k=1)[0]
        return chosen_generator()

    def generate_mobile(self) -> str:
        generators = [
            self._generate_chrome_android,
            self._generate_safari_ios,
            self._generate_safari_ipad,
            self._generate_firefox_android,
        ]
        # Weight Chrome Android and iOS Safari more heavily
        weights = [40, 35, 15, 10]
        chosen_generator = random.choices(generators, weights=weights, k=1)[0]
        return chosen_generator()

    def generate(self, prefer_mobile: bool = False) -> str:
        if prefer_mobile:
            mobile_chance = 0.75
        else:
            mobile_chance = 0.30

        if random.random() < mobile_chance:
            return self.generate_mobile()
        else:
            return self.generate_desktop()


# Global generator instance (singleton pattern)
_generator = UserAgentGenerator()


def get_random_user_agent(prefer_mobile: bool = False) -> str:
    return _generator.generate(prefer_mobile)


def get_desktop_user_agent() -> str:
    return _generator.generate_desktop()


def get_mobile_user_agent() -> str:
    return _generator.generate_mobile()


# For testing/debugging
if __name__ == "__main__":
    print("User Agent Generator - Test Output")
    print("=" * 70)

    print("\nDesktop User Agents (10 samples):")
    for i in range(10):
        print(f"{i+1:2}. {get_desktop_user_agent()}")

    print("\nMobile User Agents (10 samples):")
    for i in range(10):
        print(f"{i+1:2}. {get_mobile_user_agent()}")

    print("\nRandom Mix (prefer_mobile=False, 10 samples):")
    for i in range(10):
        ua = get_random_user_agent(prefer_mobile=False)
        device = "[Mobile]" if any(x in ua for x in ["Mobile", "Android", "iPhone", "iPad"]) else "[Desktop]"
        print(f"{i+1:2}. {device} {ua}")
