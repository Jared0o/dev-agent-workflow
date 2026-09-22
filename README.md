# Dev Agent Workflow

Plugin Codex CLI prowadzący od analizy aplikacji lub featura do przetestowanych
zmian i draft PR. Zakres kontroli zależy od ryzyka zadania.
Główna sesja prowadzi zadania i deleguje pracę natywnym agentom; trywialne
zmiany niskiego ryzyka wykonuje bezpośrednio.
Komunikacja z użytkownikiem jest po polsku, materiały robocze po angielsku.

## Instalacja

Wymagania: Codex CLI z pluginami i natywnymi agentami (implementacja przygotowana
dla `0.154.0`), Python 3.10+, Git i zalogowane `gh` do publikacji.
Modele muszą być dostępne w Twoim abonamencie Codex. Plugin nie wymaga klucza API.

```sh
gh repo clone Jared0o/dev-agent-workflow
cd dev-agent-workflow
python3 scripts/validate.py
python3 scripts/install.py
```

Instalator tworzy symlink `~/plugins/dev-agent-workflow` do tego checkoutu,
rejestruje wpis w osobistym `~/.agents/plugins/marketplace.json` i wywołuje
`codex plugin add`. Zachowuje inne wpisy i odmawia nadpisania innej instalacji.
`--register-only` pomija wywołanie Codex. Instalacja zapisuje pliki w katalogu
domowym — sandbox może wymagać uprawnienia do tej operacji.
Osobisty marketplace jest wykrywany automatycznie; nie trzeba go dodawać osobnym
`codex plugin marketplace add`.

Uruchom nową sesję w katalogu aplikacji:

```sh
codex -m gpt-6-sol -c 'model_reasoning_effort="medium"'
```

Następnie wpisz:

```text
$dev-workflow Dodaj logowanie do aplikacji Go + Next.js. Najpierw przygotuj analizę.
$dev-workflow Pokaż status zadania add-login.
$dev-workflow Wznów zadanie add-login.
```

Sol / medium to rekomendacja startowa. Orchestrator używa modelu i effort, które
wybierasz dla głównej sesji; workflow nie wymusza ich zgodności z konfiguracją.
Skill nie zmienia modelu sesji głównej. W trwającej sesji wybierz go przez `/model`.
Nazwy modeli i poziomy rozumowania są sprawdzane przez środowisko Codex; przy
niedostępności workflow zatrzymuje delegowanie i prosi o wybór zamiennika.

## Przebieg

Nowe zadania: **krótki plan → implementacja z testami i dokumentacją →
weryfikacja → oddanie zmian**. Orchestrator zapisuje poziom ryzyka i uzasadnienie.

| Ryzyko | Przykłady | Akceptacja i kontrola |
|---|---|---|
| Niskie (`low`) | Zwykły tekst dokumentacji, kosmetyka UI, jednoznaczna lokalna poprawka bez wpływu na bezpieczeństwo, trwałe dane i kontrakty | Jasne zlecenie wystarcza; trywialne zmiany wykonuje i sprawdza orchestrator, pozostałe deleguje wykonawcy |
| Standardowe (`standard`, domyślne) | Pozostałe zadania bez przesłanek wysokiego ryzyka | Akceptacja planu, wykonawca i niezależny reviewer |
| Wysokie (`high`) | Logowanie, uprawnienia, płatności, migracje, operacje destrukcyjne, zgodność publicznego API | Akceptacja planu, wykonawca, niezależny tester i reviewer |

Dla jednego zadania implementacyjnego oznacza to **0 pomocników dla trywialnego
`low`, 1 dla pozostałego `low`, 2 dla `standard` i 3 dla `high`**, bez liczenia
orchestratora, dodatkowych rund napraw i konsultacji architektury na wyraźną prośbę.
Liczba plików
nie wyznacza ryzyka. Niejasny wpływ wymaga rozpoznania; prośba o samą analizę nie
upoważnia do implementacji. Już zaakceptowanego planu nie trzeba akceptować ponownie.

Orchestrator zachowuje model Twojej sesji (zalecany GPT-6 Sol / medium).
Wykonawca, tester i reviewer standardowy używają GPT-6 Sol / medium, a reviewer
wysokiego ryzyka GPT-6 Astra / high. Wykonawca przygotowuje także dokumentację
przed weryfikacją. Osobny dokumenter GPT-6 Sol / low pozostaje tylko dla starych zadań.
Na wyraźną prośbę użytkownika orchestrator może poprosić GPT-6 Astra / high o
konsultację architektury. Konsultant tylko analizuje projekt i zwraca zalecenia,
alternatywy, konsekwencje i niewiadome; orchestrator zapisuje wnioski w specyfikacji.
Sama propozycja lub akceptacja planu nie uruchamia konsultacji. Nie zastępuje ona
wymaganych testów ani niezależnej weryfikacji.
Zmiana zakresu lub kontraktu wraca do użytkownika. Wzrost ryzyka zwiększa wymagane
kontrole i zatrzymuje zależną pracę, jeśli potrzebna jest nowa akceptacja.

Profile obejmują Go, C#/.NET i React/Next.js. Korzystają z narzędzi i wersji
zastanego projektu. REST/OpenAPI lub gRPC/protobuf wybierane są podczas analizy;
plugin nie narzuca architektury ani CMS. Tryb `direct-low` jest dostępny tylko dla
jednoznacznej zmiany tekstu, zwykłej
dokumentacji lub kosmetyki UI bez wpływu na logikę, bezpieczeństwo, dane i kontrakty.
Orchestrator zapisuje uzasadnienie, wykonuje zmianę i focused check oraz wymagane
kontrole repo. Poza tym trybem implementuje jeden wykonawca;
podział pracy służy tylko niezależnym częściom. Do trzech pomocniczych agentów może
pracować równolegle, jeżeli zakresy są niezależne. Wspólne kontrakty i lockfile
mają jednego właściciela. Tylko orchestrator wykonuje operacje Git i publikuje.

## Konfiguracja i stan

Domyślne ustawienia są w [config/defaults.json](config/defaults.json).
Opcjonalny plik aplikacji `.dev-workflow/config.json` zawiera tylko nadpisania:

```json
{
  "max_parallel_agents": 2,
  "models": {
    "implementer": {"model": "gpt-6-sol", "effort": "high"},
    "reviewer": {"model": "gpt-6-sol", "effort": "medium"}
  },
  "risk_model_overrides": {
    "high": {"reviewer": {"model": "gpt-6-astra", "effort": "high"}}
  },
  "escalation_model": {"model": "gpt-6-astra", "effort": "high"},
  "architecture_model": {"model": "gpt-6-astra", "effort": "high"}
}
```

Domyślnie dopuszczone są dwie rundy naprawy problemu i jedna próba po diagnozie
modelu `escalation_model`. Astra dostaje konkretny problem do diagnozy dopiero po
wyczerpaniu zwykłych rund; wykonawca wprowadza poprawkę, a wymagane oceny pozostają
obowiązkowe. Diagnoza nie zwiększa budżetu napraw. Ustawienie `delivery: "local"`
kończy pracę lokalnym commitem.
Ustawienia pomocników dobierane są z `models`, następnie z nadpisania dla ryzyka.
`models.orchestrator` jest wyłącznie rekomendacją startową. `architecture_model`
jest osobnym ustawieniem i nie dodaje roli do `models` ani do wymaganych ocen.
Modelowe role, limity prób i równoległości można zmieniać w konfiguracji;
zmiana konfiguracji w trakcie zadania wymaga ponownego zaakceptowania planu.

`.dev-workflow/tasks/<id>/` przechowuje krótką specyfikację, listę zadań, stan,
jeden raport weryfikacji i informacje o publikacji. Orchestrator dodaje `.dev-workflow/` do ignorowanych
plików aplikacji. Zawartość nie trafia do PR. Zapis umożliwia wznowienie w nowej
sesji; repozytoryjne zmiany i raporty są porównywane przez SHA-256. Nowe zadania
używają formatu stanu v2. Istniejące zadania v1 zachowują poprzednie etapy,
akceptację i wymagane raporty; nie są automatycznie migrowane. Stany v2 bez trybu
wykonania pozostają delegowane i zachowują poprzedni format akceptacji. Nowa
efektywna konfiguracja nadal unieważnia wcześniejszą akceptację. Starsze nadpisania
modeli, także GPT-5.6, pozostają ważne i zachowują wskazane wartości. Zmiana
domyślnych modeli lub dodanie efektywnego `architecture_model` unieważnia
wcześniejszą akceptację zadania, jeśli zmienia jego efektywną konfigurację.
Konfiguracja pozostaje w formacie v1, łącznie z rolą dokumentera dla starszych zadań.

[Opis poleceń i formatu stanu](skills/dev-workflow/references/state.md)
wyjaśnia akceptację, kontrolę zależności, zapisywanie wyników i wznowienie.
Helpery są lokalnymi narzędziami walidacji, nie silnikiem uruchamiającym modele.
Nie potwierdzają samodzielnie, że człowiek zaakceptował plan lub że test wykonano:
orchestrator musi zapisywać rzeczywiste wyniki narzędzi. Podmoduły wymagają osobnych
workflow; zmiany w ignorowanych zależnościach i zewnętrznych usługach trzeba
uwzględnić w ocenie aktualności wyników.

## Oszczędność i jakość

Agenci otrzymują krótkie pakiety zadań i odnośniki do potrzebnych plików zamiast
pełnej historii. Testy wykonują narzędzia projektu, a model ocenia ich wyniki
i sensowność scenariuszy. Ponawiane są kontrole dotknięte zmianą; zachowanie
poprzednich wyników po zmianie samej dokumentacji wymaga uzasadnionej oceny delty.
Weryfikacja wymagana dla danego ryzyka i wymagane testy blokują publikację, jeśli
nie zostały wykonane lub wykryły nierozwiązany problem. Brak narzędzia nie oznacza
wyniku pozytywnego. Reviewer wykorzystuje aktualne wyniki wykonawcy, a tester
wysokiego ryzyka koncentruje się na scenariuszach i integracjach wymagających
niezależnego sprawdzenia. Nowy agent nie oznacza automatycznie powtórzenia testów.

Podsumowanie podaje rzeczywiste modele/effort pomocników, liczbę agentów/prób
i tokeny, jeżeli runtime je udostępnia. Plugin nie odczytuje sekretów ani prywatnych logów sesji w celu pomiaru.
Nie obiecuje procentowej oszczędności ani przeliczenia tokenów na limit abonamentu.
Równoległość skraca czas części zadań, ale może zwiększać zużycie tokenów.

## GitHub i wersje

Repozytorium tego pluginu i nowo tworzone repozytoria aplikacji są prywatne.
W istniejących projektach zachowana jest widoczność repozytorium — gałąź nie ma
osobnego ustawienia prywatności. Domyślny rezultat to zwykły push gałęzi i draft PR,
bez automatycznego merge, wdrożenia czy wysyłania wiadomości do innych osób.
Brak dostępu do GitHub pozostawia gotowe zmiany lokalnie do wznowienia publikacji.

Wersjonowanie: SemVer w manifeście i tagach `v0.1.0`, `v0.2.0` itd.
Aktualizacja instalacji po opublikowanym wydaniu:

```sh
git pull --ff-only
python3 scripts/validate.py
python3 scripts/install.py
```

Rozpocznij nową sesję po reinstalacji. Przy lokalnym rozwoju tej samej wersji użyj
narzędzia `update_plugin_cachebuster.py` z umiejętności `plugin-creator`, jeśli jest
dostępna, i ponownie zainstaluj plugin; nie edytuj ręcznie istniejącego marketplace.
Wydania używają normalnej nowej wersji SemVer.

## Weryfikacja pluginu

```sh
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
```

Testy są lokalne, oparte na bibliotece standardowej i tymczasowych repozytoriach.
Nie uruchamiają płatnych modeli i nie publikują do GitHub. Walidacja struktury
nie zastępuje oceny zachowania agentów; scenariusze do prób z Codex znajdują się
w [tests/scenarios.md](tests/scenarios.md).

Podstawy integracji: [natywni agenci Codex](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[pluginy](https://learn.chatgpt.com/docs/plugins),
[dobór i zachowanie GPT-6 Astra](https://developers.openai.com/api/docs/guides/latest-model).
